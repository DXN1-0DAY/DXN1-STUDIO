/* DXN1 STUDIO — web renderer logic. Talks ONLY to the localhost
   bridge (/api/*, token-guarded). No frameworks, no build step. */
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/&/g, "&amp;")
  .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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

/* ---------- syntax highlighting (tiny, no deps) ---------- */
const PY_KW = ("def|class|return|if|elif|else|for|while|import|from|as|" +
  "with|try|except|finally|raise|pass|break|continue|and|or|not|in|is|" +
  "None|True|False|lambda|global|nonlocal|assert|yield|async|await|del|" +
  "self|match|case").split("|");
const JS_KW = ("function|const|let|var|return|if|else|for|while|do|switch|" +
  "case|break|continue|new|this|typeof|instanceof|class|extends|super|" +
  "import|export|from|default|async|await|try|catch|finally|throw|" +
  "null|undefined|true|false|of|in").split("|");

function langFor(name) {
  const ext = (name.split(".").pop() || "").toLowerCase();
  if (ext === "py") return "py";
  if (["js", "mjs", "cjs", "ts"].includes(ext)) return "js";
  if (["json"].includes(ext)) return "js";
  return null;
}

const RULES = {
  py: [
    [/#[^\n]*/g, "tk-cmt"],
    [/("""[\s\S]*?"""|'''[\s\S]*?''')/g, "tk-str"],
    [/(f?"(?:\\.|[^"\\\n])*"|f?'(?:\\.|[^'\\\n])*')/g, "tk-str"],
    [/(@[\w.]+)/g, "tk-dec"],
    [new RegExp("\\b(" + PY_KW.join("|") + ")\\b", "g"), "tk-kw"],
    [/(\b\d+(?:\.\d+)?\b)/g, "tk-num"],
  ],
  js: [
    [/\/\/[^\n]*/g, "tk-cmt"],
    [/\/\*[\s\S]*?\*\//g, "tk-cmt"],
    [/(`(?:\\.|[^`\\])*`)/g, "tk-str"],
    [/("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')/g, "tk-str"],
    [new RegExp("\\b(" + JS_KW.join("|") + ")\\b", "g"), "tk-kw"],
    [/(\b\d+(?:\.\d+)?\b)/g, "tk-num"],
  ],
};

function highlight(src, lang) {
  if (!lang || !RULES[lang]) return esc(src) + "\n";
  const rules = RULES[lang];
  // tokenize: collect non-overlapping spans, earlier rules win
  const spans = [];
  for (const [re, cls] of rules) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(src)) !== null) {
      if (m[0].length === 0) { re.lastIndex++; continue; }
      spans.push({ start: m.index, end: m.index + m[0].length, cls,
                   text: m[0] });
      if (m[0].length === 0) break;
    }
  }
  spans.sort((a, b) => a.start - b.start ||
              (b.end - b.start) - (a.end - a.start));
  const kept = [];
  let last = 0;
  for (const s of spans) {
    if (s.start >= last) { kept.push(s); last = s.end; }
  }
  let out = "", pos = 0;
  for (const s of kept) {
    out += esc(src.slice(pos, s.start));
    out += `<span class="${s.cls}">${esc(s.text)}</span>`;
    pos = s.end;
  }
  out += esc(src.slice(pos));
  return out + "\n";
}

function renderHighlight() {
  const ta = $("editor");
  const lang = currentFile ? langFor(currentFile) : null;
  $("highlight").innerHTML = "<code>" +
    (ta.value ? highlight(ta.value, lang)
              : esc(ta.placeholder)) + "</code>";
  syncScroll();
}

function syncScroll() {
  const ta = $("editor"), hl = $("highlight");
  hl.scrollTop = ta.scrollTop;
  hl.scrollLeft = ta.scrollLeft;
}

/* ---------- tabs / editor ---------- */
function renderTabs() {
  const bar = $("tabbar");
  bar.innerHTML = "";
  for (const tb of STATE.tabs) {
    const el = document.createElement("div");
    el.className = "tab" +
      (tb.path === currentFile ? " active" : "");
    el.innerHTML = `<span>${esc(tb.name)}</span>` +
      ((tb.dirty || (tb.path === currentFile && dirtyLocal)) ?
       `<span class="dot">●</span>` : "");
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
  $("st-file").textContent = currentFile;
  renderGutter();
  renderHighlight();
  renderTabs();
  toast("Opened " + path.split("/").pop());
}

async function saveFile() {
  if (!currentFile) return toast("No file open");
  const r = await (await api("/api/file", {
    method: "POST",
    body: JSON.stringify({ path: currentFile, content: $("editor").value }),
  })).json();
  if (r.ok) { dirtyLocal = false; renderTabs();
    toast("Saved " + currentFile.split("/").pop()); }
  else toast("Save failed: " + (r.error || "?"));
}

/* ---------- explorer ---------- */
async function renderTree() {
  const r = await (await api("/api/tree")).json();
  const tree = $("tree");
  if (!r.ok) return;
  tree.innerHTML = "";
  for (const item of r.tree) {
    tree.appendChild(treeRow(item, ""));
    if (item.dir) {
      const wrap = document.createElement("div");
      wrap.className = "kids";
      wrap.style.marginLeft = "14px";
      wrap.style.display = "none";
      for (const kid of item.children || []) {
        const isDir = !kid.includes(".") || false;
        const row = treeRow({ name: kid, dir: false }, item.name + "/");
        row.style.opacity = ".85";
        wrap.appendChild(row);
      }
      tree.appendChild(wrap);
      item._wrap = wrap;
    }
  }
}

function treeRow(item, prefix) {
  const el = document.createElement("div");
  el.className = "tree-item" + (item.dir ? " dir" : "");
  el.innerHTML = `<span class="ico">${item.dir ? "▸" : "·"}</span>` +
    `<span class="nm">${esc(item.name)}</span>` +
    `<span class="act">` +
    (item.dir ? "" :
      `<button title="Rename" data-a="ren">⋈</button>`) +
    `<button class="danger" title="Delete" data-a="del">✕</button>` +
    `</span>`;
  el.querySelector(".nm").onclick = async () => {
    if (item.dir) {
      if (item._wrap) {
        const open = item._wrap.style.display !== "none";
        item._wrap.style.display = open ? "none" : "block";
        el.querySelector(".ico").textContent = open ? "▸" : "▾";
      }
    } else {
      openFile(prefix + item.name);
    }
  };
  const del = el.querySelector('[data-a="del"]');
  del.onclick = async (e) => {
    e.stopPropagation();
    const p = prefix + item.name;
    if (!confirm("Delete " + p + "?")) return;
    const r = await (await api("/api/delete", {
      method: "POST", body: JSON.stringify({ path: p }) })).json();
    if (r.ok) { toast("Deleted " + p); renderTree(); }
    else toast("Delete failed: " + (r.error || "?"));
  };
  const ren = el.querySelector('[data-a="ren"]');
  if (ren) ren.onclick = async (e) => {
    e.stopPropagation();
    const p = prefix + item.name;
    const to = prompt("Rename " + p + " to:", item.name);
    if (!to || to === item.name) return;
    const r = await (await api("/api/rename", {
      method: "POST",
      body: JSON.stringify({ path: p, to: prefix + to }) })).json();
    if (r.ok) { toast("Renamed to " + to); renderTree(); }
    else toast("Rename failed: " + (r.error || "?"));
  };
  return el;
}

$("btn-newfile").onclick = async () => {
  const name = prompt("New file name:", "untitled.py");
  if (!name) return;
  const r = await (await api("/api/new_file", {
    method: "POST", body: JSON.stringify({ path: name }) })).json();
  if (r.ok) { toast("Created " + name); renderTree(); openFile(name); }
  else toast("Create failed: " + (r.error || "?"));
};
$("btn-newdir").onclick = async () => {
  const name = prompt("New folder name:", "src");
  if (!name) return;
  const r = await (await api("/api/mkdir", {
    method: "POST", body: JSON.stringify({ path: name }) })).json();
  if (r.ok) { toast("Created " + name + "/"); renderTree(); }
  else toast("Create failed: " + (r.error || "?"));
};

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
  if (palSel >= items.length) palSel = Math.max(0, items.length - 1);
  list.innerHTML = "";
  items.forEach((c, i) => {
    const el = document.createElement("div");
    el.className = "pal-item" + (i === palSel ? " sel" : "");
    el.innerHTML = `<span>${esc(c.label)}</span>` +
      (c.key ? `<span class="k">${esc(c.key)}</span>` : "");
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
$("editor").addEventListener("input", () => {
  dirtyLocal = true;
  renderGutter();
  renderHighlight();
  renderTabs();
});
$("editor").addEventListener("scroll", syncScroll);
$("editor").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveFile(); }
  if (e.key === "Tab") {  // real tabs in the editor
    e.preventDefault();
    const ta = e.target, s = ta.selectionStart, en = ta.selectionEnd;
    ta.value = ta.value.slice(0, s) + "    " + ta.value.slice(en);
    ta.selectionStart = ta.selectionEnd = s + 4;
    dirtyLocal = true; renderHighlight(); renderGutter();
  }
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
  if ((e.ctrlKey || e.metaKey) && e.key === "s") {
    e.preventDefault(); saveFile();
  }
});

/* ---------- boot ---------- */
poll();
renderTree();
renderHighlight();
loadCommands();
setInterval(poll, 1200);
setInterval(renderTree, 8000);
