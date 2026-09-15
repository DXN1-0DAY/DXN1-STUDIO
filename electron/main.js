// DXN1 STUDIO — Electron main process.
// Spawns the Python engine bridge (dxn1_studio/bridge.py) and forwards
// renderer requests to it over stdin/stdout (newline-delimited JSON).
// Everything else (dialogs, clipboard, window controls) is plain IPC.
'use strict';

const { app, BrowserWindow, ipcMain, dialog, clipboard, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const REPO_ROOT = path.join(__dirname, '..');
const BRIDGE_SCRIPT = path.join(REPO_ROOT, 'dxn1_studio', 'bridge.py');
const REQUEST_TIMEOUT_MS = 30000;

let mainWindow = null;
let bridgeProc = null;
let bridgeAlive = false;
let nextId = 1;
const pending = new Map(); // id -> {resolve, reject, timer}

// ---------------------------------------------------------------- bridge
function pythonCandidates() {
  const list = [];
  if (process.env.DXN1_PYTHON) list.push(process.env.DXN1_PYTHON);
  if (process.platform === 'win32') list.push('python', 'python3', 'py');
  else list.push('python3', 'python');
  return list;
}

function sendToBridge(payload) {
  if (!bridgeProc || !bridgeAlive) throw new Error('bridge not running');
  bridgeProc.stdin.write(JSON.stringify(payload) + '\n');
}

function killBridge() {
  if (bridgeProc) {
    try { bridgeProc.kill(); } catch (_) { /* already gone */ }
    bridgeProc = null;
    bridgeAlive = false;
  }
}

function startBridge() {
  const workspace = process.env.DXN1_WORKSPACE || REPO_ROOT;
  const candidates = pythonCandidates();
  tryNext(0);

  function tryNext(i) {
    if (i >= candidates.length) {
      bridgeAlive = false;
      if (mainWindow) mainWindow.webContents.send('dxn1-bridge-dead', {
        reason: 'no python found — demo mode',
      });
      return;
    }
    const py = candidates[i];
    let proc;
    try {
      proc = spawn(py, [BRIDGE_SCRIPT, workspace], {
        cwd: REPO_ROOT,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: Object.assign({}, process.env, { PYTHONUNBUFFERED: '1' }),
      });
    } catch (err) {
      tryNext(i + 1);
      return;
    }
    let sawHello = false;
    let buf = '';

    proc.stdout.on('data', (chunk) => {
      buf += chunk.toString('utf8');
      let nl;
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl);
        buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        let msg;
        try { msg = JSON.parse(line); } catch (_) { continue; }
        const p = pending.get(msg.id);
        if (p) {
          clearTimeout(p.timer);
          pending.delete(msg.id);
          if (msg.ok) p.resolve(msg.result);
          else p.reject(new Error(msg.error || 'bridge error'));
        }
      }
    });

    proc.stderr.on('data', (chunk) => {
      // engine stderr is diagnostics only — keep it on our console
      console.error('[bridge]', chunk.toString('utf8').trimEnd());
    });

    proc.on('error', () => {           // spawn failure (ENOENT etc.)
      if (!sawHello) tryNext(i + 1);
    });

    proc.on('exit', () => {
      const wasAlive = bridgeAlive;
      bridgeAlive = false;
      bridgeProc = null;
      for (const [, p] of pending) {
        clearTimeout(p.timer);
        p.reject(new Error('bridge exited'));
      }
      pending.clear();
      if (wasAlive && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('dxn1-bridge-dead', {
          reason: 'engine exited — demo mode',
        });
      }
    });

    // probe: a hello roundtrip decides if this python works
    const probe = { id: 0, cmd: 'hello', args: {} };
    const timer = setTimeout(() => {
      try { proc.kill(); } catch (_) {}
      if (!sawHello) tryNext(i + 1);
    }, 6000);
    pending.set(0, {
      resolve: (result) => {
        clearTimeout(timer);
        sawHello = true;
        bridgeProc = proc;
        bridgeAlive = true;
        console.log('[bridge] engine up:', result && result.version,
          'on', py);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('dxn1-bridge-up', result);
        }
      },
      reject: (err) => {
        clearTimeout(timer);
        try { proc.kill(); } catch (_) {}
        tryNext(i + 1);
      },
      timer,
    });
    try {
      proc.stdin.write(JSON.stringify(probe) + '\n');
    } catch (_) {
      clearTimeout(timer);
      tryNext(i + 1);
    }
  }
}

function request(cmd, args) {
  return new Promise((resolve, reject) => {
    if (!bridgeAlive) { reject(new Error('bridge not running')); return; }
    const id = nextId++;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`bridge timeout: ${cmd}`));
    }, REQUEST_TIMEOUT_MS);
    pending.set(id, { resolve, reject, timer });
    try {
      sendToBridge({ id, cmd, args: args || {} });
    } catch (err) {
      clearTimeout(timer);
      pending.delete(id);
      reject(err);
    }
  });
}

// ------------------------------------------------------------------- ipc
ipcMain.handle('dxn1-request', async (_e, { cmd, args }) => {
  try {
    return { ok: true, result: await request(cmd, args) };
  } catch (err) {
    return { ok: false, error: err && err.message };
  }
});

ipcMain.handle('dxn1-dialog', async (_e, kind, opts) => {
  const win = BrowserWindow.getFocusedWindow() || mainWindow;
  const o = opts || {};
  if (kind === 'openFile') {
    const r = await dialog.showOpenDialog(win, {
      properties: ['openFile'],
      filters: o.filters || [],
    });
    return r.canceled ? null : r.filePaths[0];
  }
  if (kind === 'openDirectory') {
    const r = await dialog.showOpenDialog(win, {
      properties: ['openDirectory'],
    });
    return r.canceled ? null : r.filePaths[0];
  }
  if (kind === 'save') {
    const r = await dialog.showSaveDialog(win, {
      defaultPath: o.defaultPath || undefined,
    });
    return r.canceled ? null : r.filePath;
  }
  return null;
});

ipcMain.handle('dxn1-win', (_e, action) => {
  const win = mainWindow;
  if (!win) return null;
  if (action === 'minimize') win.minimize();
  else if (action === 'maximize') {
    if (win.isMaximized()) win.unmaximize(); else win.maximize();
  } else if (action === 'close') win.close();
  else if (action === 'isMaximized') return win.isMaximized();
  return null;
});

ipcMain.handle('dxn1-clipboard', (_e, text) => {
  clipboard.writeText(String(text == null ? '' : text));
  return true;
});

ipcMain.handle('dxn1-external', (_e, url) => {
  if (typeof url === 'string' && url.startsWith('http')) {
    shell.openExternal(url);
    return true;
  }
  return false;
});

// ---------------------------------------------------------------- window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 940,
    minHeight: 600,
    frame: false,
    backgroundColor: '#0d1117',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('maximize', () =>
    mainWindow.webContents.send('dxn1-win-state', 'maximized'));
  mainWindow.on('unmaximize', () =>
    mainWindow.webContents.send('dxn1-win-state', 'restored'));
  mainWindow.on('closed', () => { mainWindow = null; });
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
  app.whenReady().then(() => {
    startBridge();
    createWindow();
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });
  app.on('window-all-closed', () => {
    killBridge();
    app.quit();
  });
  app.on('before-quit', killBridge);
}
