// DXN1 STUDIO 3 — Electron main process.
// The face spawns the Python engine (the brain) and pipes every
// request to it over stdio. One window, frameless, beautiful.

const { app, BrowserWindow, ipcMain, dialog, clipboard } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const ROOT = path.join(__dirname, "..");
let win = null;
let engine = null;
let engineCandidates = [];
let pending = new Map();      // id -> {resolve, reject, timer}
let reqId = 0;
let engineUp = false;

const PY_CANDIDATES = () => {
  const list = [];
  if (process.env.DXN1_PYTHON) list.push(process.env.DXN1_PYTHON);
  list.push("python3", "python");
  return list;
};

// --------------------------------------------------------------- engine
function engineRequest(cmd, args, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    if (!engine || !engine.stdin.writable) {
      return reject(new Error("engine is not running"));
    }
    const id = ++reqId;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`engine timed out on ${cmd}`));
    }, timeoutMs);
    pending.set(id, { resolve, reject, timer });
    engine.stdin.write(JSON.stringify({ id, cmd, args }) + "\n");
  });
}

function engineLine(line) {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }  // noise is dropped
  const entry = pending.get(msg.id);
  if (!entry) return;
  pending.delete(msg.id);
  clearTimeout(entry.timer);
  if (msg.ok) entry.resolve(msg.result);
  else entry.reject(new Error(msg.error || "engine error"));
}

function engineDead(code) {
  engineUp = false;
  pending.forEach((p) => {
    clearTimeout(p.timer);
    p.reject(new Error("engine exited"));
  });
  pending.clear();
  if (win && !win.isDestroyed()) {
    win.webContents.send("dxn1:engine", { up: false, code });
  }
}

function engineStart() {
  const workspace = process.env.DXN1_WORKSPACE || ROOT;
  engineCandidates = PY_CANDIDATES();

  const tryNext = () => {
    const py = engineCandidates.shift();
    if (!py) {
      // no Python at all — the face keeps working in demo mode
      if (win && !win.isDestroyed()) {
        win.webContents.send("dxn1:engine", { up: false, demo: true });
      }
      return;
    }
    const child = spawn(py, ["-m", "engine", workspace], {
      cwd: ROOT,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
      stdio: ["pipe", "pipe", "pipe"],
    });
    let probed = false;
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      for (const line of chunk.split("\n")) {
        if (line.trim()) engineLine(line);
      }
      if (!probed) {
        probed = true;
        engineUp = true;
        if (win && !win.isDestroyed()) {
          win.webContents.send("dxn1:engine", { up: true });
        }
      }
    });
    child.stderr.on("data", () => {/* engine stderr is log noise */});
    child.on("error", () => { if (!engineUp) tryNext(); });
    child.on("exit", (code) => engineDead(code));

    // hello probe: a candidate that cannot speak dies here
    engineRequest("hello", {}, 6000)
      .then((info) => {
        engine = child;
        if (win && !win.isDestroyed()) {
          win.webContents.send("dxn1:engine", { up: true, info });
        }
      })
      .catch(() => {
        try { child.kill(); } catch {}
        if (!engineUp) tryNext();
      });
  };
  tryNext();
}

function createWindow() {
  win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 640,
    frame: false,
    backgroundColor: "#07080d",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false,
    },
  });

  win.loadFile(path.join(ROOT, "renderer", "index.html"));
  win.once("ready-to-show", () => win.show());

  // a fresh engine answer goes straight to the waiting face
  win.webContents.on("did-finish-load", () => {
    win.webContents.send("dxn1:engine", { up: engineUp });
  });
}

// ------------------------------------------------------------------ ipc
ipcMain.handle("dxn1:request", (_e, { cmd, args }) => {
  return engineRequest(cmd, args).then(
    (result) => ({ ok: true, result }),
    (err) => ({ ok: false, error: String(err.message || err) }));
});

ipcMain.handle("dxn1:win", (_e, action) => {
  if (!win) return false;
  if (action === "min") win.minimize();
  else if (action === "max") win.isMaximized() ? win.unmaximize() : win.maximize();
  else if (action === "close") win.close();
  else if (action === "maximized") return win.isMaximized();
  return true;
});

ipcMain.handle("dxn1:dialog", async (_e, opts) => {
  const res = await dialog.showOpenDialog(win, {
    properties: ["openDirectory"],
    ...opts,
  });
  return res.canceled ? null : res.filePaths[0] || null;
});

ipcMain.handle("dxn1:clipboard", (_e, text) => {
  clipboard.writeText(String(text ?? ""));
  return true;
});

ipcMain.handle("dxn1:external", (_e, url) => {
  if (/^https?:\/\//.test(String(url))) {
    const { shell } = require("electron");
    shell.openExternal(url);
    return true;
  }
  return false;
});

// ----------------------------------------------------------------- boot
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) { win.restore(); win.focus(); }
  });
  app.whenReady().then(() => {
    createWindow();
    engineStart();
  });
  app.on("window-all-closed", () => app.quit());
}
