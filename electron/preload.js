// DXN1 STUDIO — preload: the only bridge between the renderer and
// the OS. Exposes a tiny, promise-based `window.dxn1` API.
'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('dxn1', {
  // engine requests -> Python bridge
  request: (cmd, args) => ipcRenderer.invoke('dxn1-request', { cmd, args }),
  // native dialogs: 'openFile' | 'openDirectory' | 'save'
  dialog: (kind, opts) => ipcRenderer.invoke('dxn1-dialog', kind, opts),
  // frameless window controls: 'minimize' | 'maximize' | 'close' | 'isMaximized'
  win: (action) => ipcRenderer.invoke('dxn1-win', action),
  winState: (cb) => ipcRenderer.on('dxn1-win-state', (_e, s) => cb(s)),
  clipboardWrite: (text) => ipcRenderer.invoke('dxn1-clipboard', text),
  openExternal: (url) => ipcRenderer.invoke('dxn1-external', url),
  onBridgeUp: (cb) => ipcRenderer.on('dxn1-bridge-up', (_e, info) => cb(info)),
  onBridgeDead: (cb) => ipcRenderer.on('dxn1-bridge-dead', (_e, info) => cb(info)),
  platform: process.platform,
  electron: process.versions.electron,
});
