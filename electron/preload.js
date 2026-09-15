// DXN1 STUDIO — preload. Deliberately minimal: the renderer talks to
// the Python bridge over HTTP with the session token; nothing from
// Node is exposed to the page.
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("dxn1", {
  shell: "electron",
  platform: process.platform,
});
