// DXN1 STUDIO 3 — preload. The face sees ONLY this bridge:
// contextIsolation on, nodeIntegration off, a tiny typed surface.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("dxn1", {
  // the brain: request(cmd, args) -> {ok, result} | {ok, error}
  request: (cmd, args) => ipcRenderer.invoke("dxn1:request", { cmd, args }),

  // window controls (frameless titlebar)
  win: (action) => ipcRenderer.invoke("dxn1:win", action),

  // native folder picker -> path | null
  pickFolder: (opts) => ipcRenderer.invoke("dxn1:dialog", opts),

  // clipboard + safe external links
  clipboardWrite: (text) => ipcRenderer.invoke("dxn1:clipboard", text),
  openExternal: (url) => ipcRenderer.invoke("dxn1:external", url),

  // engine lifecycle broadcasts
  onEngine: (fn) => {
    const h = (_e, data) => fn(data);
    ipcRenderer.on("dxn1:engine", h);
    return () => ipcRenderer.removeListener("dxn1:engine", h);
  },

  platform: process.platform,
  electron: true,
});
