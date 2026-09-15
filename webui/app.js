/* DXN1 STUDIO — web renderer logic. Talks ONLY to the localhost
   bridge (/api/*, token-guarded). No frameworks, no build step. */
"use strict";

const $ = (id) => document.getElementById(id);
const TOKEN = new URLSearchParams(location.search).get("token") ||
  localStorage.getItem("dxn1_token") || "";
const api = (path, opts = {}) => fetch(path, {
  ...opts,
  headers: { "Content-Type": "application/json",
             "X-DXN1-Token": TOKEN, ...(opts.headers || {}) },
});

let STATE = { tabs: [], theme: {} };
let CMDS = [];
let currentFile = null;
let palSel = 0;
let dirtyLocal = false;

/* ---------- theme tokens ---------- */
function applyTheme(t) {
  if (!t) return;
  const r = document.documentElement.style;
  const map = { bg: "--bg", sidebar: "--sidebar", header: "--header",
    editor: "--editor", terminal: "--terminal", statusbar: "--statusbar",
    border: "--border", hover: "--hover", text: "--text",
    text_secondary: "--text2", text_muted: "--muted", card: "--card",
    card_border: "--cardb", accent: "--accent", success: "--success" };
  for (const [k, v] of Object.entries(map)) if (t[k]) r.setProperty(v, t[k]);
}

/* ---------- toast ---------- */
let toastTimer = null;
function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 2400);
}

/* ---------- editor / tabs ---------- */
function renderTabs() {
  const bar = $("tabbar");
  bar.innerHTML = "";
  for (const tb of STATE.tabs) {
    const el = document.createElement("div");
    el.className = "tab" + (tb.active ? " active" : "");
    el.innerHTML = `<span>${tb.name}</span>` +
      (tb.dirty ? `<span class="dot">●</span>` : "");
    el.onclick = () => openFile(tb.path);
    bar.appendChild(el);
  }
}

function renderGutter() {
  const lines = $("editor").value.split("\n").length || 1;
  $("gutter").textContent = Array.from({ length: lines },
    (_, i) => i + 1).join("\n");
}

async function openFile(path) {
  const r = await (await api("/api/file?path=" + encodeURIComponent(path))).json();
  if (!r.ok) return toast("Open failed: " + (r.error || "?"));
  currentFile = r.file.path;
  $("editor").value = r.file.content;
  dirtyLocal = false;
  renderGutter();
  const name = path.split("/").pop();
  $("tabbar").querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  for (const tb of STATE.tabs) if (tb.path === path) { /* active flag */ }
  toast("Opened " + name);
}

async function saveFile() {
  if (!currentFile) return toast("No file open");
  const r = await (await api("/api/file", {
    method: "POST",
    body: JSON.stringify({ path: currentFile, content: $("editor").value }),
  })).json();
  if (r.ok) { dirtyLocal = false; toast("Saved " + currentFile.split("/").pop()); }
  else toast("Save failed: " + (r.error || "?"));
}

/* ---------- explorer ---------- */
async function renderTree() {
  const r = await (await api("/api/tree")).json();
  const tree = $("tree");
  tree.innerHTML = "";
  if (!r.ok) return;
  for (const item of r.tree) {
    const el = document.createElement("div");
    el.className = "tree-item" + (item.dir ? " dir" : "");
    el.innerHTML = `<span class="ico">${item.dir ? "▸" : "·"}</span>` +
      `<span>${item.name}</span>`;
    if (item.dir) {
      el.onclick = () => el.querySelector(".kids")?.remove() ||
        void 0; // dirs expand in a later build; click is honest no-op today
      el.style.opacity = item.children ? "1" : ".8";
    } else {
      el.onclick = () => openFile(item.name);
    }
    tree.appendChild(el);
  }
}

/* ---------- terminal + status ---------- */
function renderState() {
  applyTheme(STATE.theme);
  renderTabs();
  $("ws-name").textContent = STATE.workspace
    ? STATE.workspace.split("/").pop() : "no workspace";
  $("st-status").textContent = STATE.status || "ready";
  $("st-version").textContent = STATE.version || "DXN1";
  const log = $("term-log");
  if (log.textContent !== STATE.terminal_tail) {
    log.textContent = STATE.terminal_tail || "";
    log.scrollTop = log.scrollHeight;
  }
}

async function poll() {
  try {
    const r = await (await api("/api/state")).json();
    if (r.ok) { STATE = r; renderState(); }
  } catch (e) { /* bridge restarting — keep last frame */ }
}

/* ---------- command palette ---------- */
async function loadCommands() {
  const r = await (await api("/api/commands")).json();
  CMDS = r.ok ? r.commands : [];
}

function palRender(q) {
  const list = $("palette-list");
  const ql = (q || "").toLowerCase();
  const items = CMDS.filter(c => c.label.toLowerCase().includes(ql))
    .slice(0, 60);
  palSel = Math.min(palSel, Math.max(0, items.length - 1));
  list.innerHTML = "";
  items.forEach((c, i) => {
    const el = document.createElement("div");
    el.className = "pal-item" + (i === palSel ? " sel" : "");
    el.innerHTML = `<span>${c.label}</span>` +
      (c.key ? `<span class="k">${c.key}</span>` : "");
    el.onclick = () => palRun(c);
    list.appendChild(el);
  });
  return items;
}

async function palRun(cmd) {
  $("palette-overlay").classList.add("hidden");
  const r = await (await api("/api/command", {
    method: "POST", body: JSON.stringify({ index: cmd.index }),
  })).json();
  if (r.ok) toast("▶ " + r.ran); else toast("Failed: " + (r.error || "?"));
}

function palOpen() {
  $("palette-overlay").classList.remove("hidden");
  const inp = $("palette-input");
  inp.value = ""; palSel = 0; palRender("");
  setTimeout(() => inp.focus(), 30);
}

/* ---------- wire up ---------- */
$("editor").addEventListener("input", () => { dirtyLocal = true; renderGutter(); });
$("editor").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveFile(); }
});
$("btn-run").onclick = async () => {
  await api("/api/run", { method: "POST", body: "{}" });
  toast("▶ Run requested");
};
$("btn-palette").onclick = palOpen;
$("palette-input").addEventListener("input", (e) => { palSel = 0; palRender(e.target.value); });
$("palette-input").addEventListener("keydown", (e) => {
  const items = palRender(e.target.value);
  if (e.key === "ArrowDown") { e.preventDefault(); palSel = Math.min(palSel + 1, items.length - 1); palRender(e.target.value); }
  else if (e.key === "ArrowUp") { e.preventDefault(); palSel = Math.max(palSel - 1, 0); palRender(e.target.value); }
  else if (e.key === "Enter" && items[palSel]) { e.preventDefault(); palRun(items[palSel]); }
  else if (e.key === "Escape") $("palette-overlay").classList.add("hidden");
});
$("palette-overlay").addEventListener("mousedown", (e) => {
  if (e.target.id === "palette-overlay") $("palette-overlay").classList.add("hidden");
});
window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault(); palOpen();
  }
});

/* ---------- boot ---------- */
poll();
renderTree();
loadCommands();
setInterval(poll, 1200);
setInterval(renderTree, 6000);
