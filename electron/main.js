// DXN1 STUDIO — Electron shell.
// Wraps the web renderer (served by the Python bridge) in a native
// desktop window. The Python core stays the brain; this file is only
// the window.
//
//   cd electron && npm install && npm start -- --url http://127.0.0.1:PORT/?token=TOKEN
//
const { app, BrowserWindow, Menu, shell } = require("electron");
const path = require("path");

function parseArgs() {
  const argv = process.argv.slice(process.defaultApp ? 2 : 1);
  const i = argv.indexOf("--url");
  return { url: i >= 0 ? argv[i + 1] : process.env.DXN1_URL || null };
}

function createWindow(url) {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 960,
    minHeight: 620,
    backgroundColor: "#0d1117",
    title: "DXN1 STUDIO",
    autoHideMenuBar: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  });

  const menu = Menu.buildFromTemplate([
    {
      label: "DXN1",
      submenu: [
        { role: "about" },
        { type: "separator" },
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Help",
      submenu: [
        {
          label: "Repository",
          click: () => shell.openExternal(
            "https://github.com/DXN1-termux/DXN1-STUDIO"),
        },
      ],
    },
  ]);
  Menu.setApplicationMenu(menu);

  if (url) {
    win.loadURL(url);
  } else {
    // No bridge URL yet — show the ramp page that explains the one
    // command to run inside the studio (palette: "Web UI / Electron").
    win.loadFile(path.join(__dirname, "ramp.html"));
  }
  win.webContents.setWindowOpenHandler(({ url: target }) => {
    shell.openExternal(target);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  createWindow(parseArgs().url);
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow(parseArgs().url);
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
