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
  // tell the Tk side too — the file joins _buffers, so the tab bar
  // and the desktop app show the same open set (single source of truth)
  api("/api/open", { method: "POST", body: JSON.stringify({ path: r.file.path }) })
    .catch(() => {});
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
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "p") {
    e.preventDefault(); qoOpen();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "s") {
    e.preventDefault(); saveFile();
  }
});

/* ---------- quick open (Ctrl+P) ---------- */
let QO_ITEMS = [];
let qoSel = 0;

async function qoOpen() {
  $("quickopen-overlay").classList.remove("hidden");
  const inp = $("quickopen-input");
  inp.value = ""; qoSel = 0; qoRender("");
  let files = [];
  try {
    const r = await (await api("/api/files")).json();
    if (r.ok) files = r.files;
  } catch (e) { /* bridge offline */ }
  // current file first, then alphabetical
  files = [...files.filter(f => f !== currentFile)].sort();
  if (currentFile) files.unshift(currentFile);
  QO_ITEMS = files;
  qoRender(inp.value);
  setTimeout(() => inp.focus(), 30);
}

function qoFuzzy(query, path) {
  // subsequence match on the basename, else substring on the path
  const base = path.split("/").pop().toLowerCase();
  const q = query.toLowerCase();
  if (!q) return true;
  let i = 0;
  for (const ch of base) if (ch === q[i]) i++;
  return i === q.length || path.toLowerCase().includes(q);
}

function qoRender(q) {
  const list = $("quickopen-list");
  const items = QO_ITEMS.filter(f => qoFuzzy(q, f)).slice(0, 50);
  if (qoSel >= items.length) qoSel = Math.max(0, items.length - 1);
  list.innerHTML = items.map((f, i) => {
    const base = f.split("/").pop();
    const dir = f.includes("/") ?
      `<span class="k">${esc(f.slice(0, f.length - base.length - 1))}</span>` : "";
    return `<div class="pal-item" data-i="${i}">` +
      `<span>${esc(base)}</span>${dir}</div>`;
  }).join("") || `<div class="pal-item">No files match.</div>`;
  list.querySelectorAll("[data-i]").forEach(el => {
    if (+el.dataset.i === qoSel) el.classList.add("sel");
    el.onclick = () => qoPick(items[+el.dataset.i]);
  });
  return items;
}

function qoPick(path) {
  $("quickopen-overlay").classList.add("hidden");
  openFile(path);
}

$("quickopen-input").addEventListener("input", (e) => {
  qoSel = 0; qoRender(e.target.value);
});
$("quickopen-input").addEventListener("keydown", (e) => {
  const items = qoRender(e.target.value);
  if (e.key === "ArrowDown") { e.preventDefault(); qoSel = Math.min(qoSel + 1, items.length - 1); qoRender(e.target.value); }
  else if (e.key === "ArrowUp") { e.preventDefault(); qoSel = Math.max(qoSel - 1, 0); qoRender(e.target.value); }
  else if (e.key === "Enter" && items[qoSel]) { e.preventDefault(); qoPick(items[qoSel]); }
  else if (e.key === "Escape") $("quickopen-overlay").classList.add("hidden");
});
$("quickopen-overlay").addEventListener("mousedown", (e) => {
  if (e.target.id === "quickopen-overlay")
    $("quickopen-overlay").classList.add("hidden");
});

/* ---------- git panel ---------- */
async function loadGit() {
  try {
    const r = await (await api("/api/git")).json();
    if (!r.ok) {
      $("git-branch").textContent = "not a git repo";
      $("git-files").innerHTML = "";
      $("git-log").innerHTML = "";
      return;
    }
    $("git-branch").innerHTML = `⎇ <b>${esc(r.branch)}</b>` +
      (r.dirty ? ` <span class="dot">● ${r.dirty} changed</span>` :
                 ` <span class="git-empty" style="display:inline">clean</span>`);
    const files = $("git-files");
    files.innerHTML = r.files.length
      ? r.files.map(f => `<div class="git-file">✎ ${esc(f)}</div>`).join("")
      : `<div class="git-empty">Nothing to commit — working tree clean.</div>`;
    const log = $("git-log");
    log.innerHTML = (r.commits || [])
      .map(c => `<div>${esc(c)}</div>`).join("") ||
      `<div class="git-empty">No commits yet.</div>`;
  } catch (e) { /* bridge offline */ }
}

async function gitAction(action, extra = {}) {
  const r = await (await api("/api/git", {
    method: "POST",
    body: JSON.stringify({ action, ...extra }) })).json();
  if (r.ok) {
    toast(`${action} ✓ ${r.detail || ""}`.trim());
    loadGit();
    poll();
  } else toast(`${action} failed: ${r.error || "?"}`);
  return r.ok;
}

$("git-chip").onclick = () => {
  $("git-overlay").classList.remove("hidden");
  loadGit();
};
$("git-overlay").addEventListener("mousedown", (e) => {
  if (e.target.id === "git-overlay")
    $("git-overlay").classList.add("hidden");
});
$("git-commit").onclick = async () => {
  const msg = $("git-msg").value.trim();
  if (!msg) return toast("Type a commit message first");
  $("git-msg").value = "";
  await gitAction("commit", { message: msg });
};
$("git-msg").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("git-commit").click();
});
$("git-push").onclick = () => gitAction("push");
$("git-pull").onclick = () => gitAction("pull");
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    $("git-overlay").classList.add("hidden");
    $("settings-overlay").classList.add("hidden");
  }
});

/* ---------- settings ---------- */
let ACCENT_HEX = {};

async function loadConfig() {
  try {
    const r = await (await api("/api/config")).json();
    if (!r.ok) return;
    const c = r.config;
    $("set-theme").value = c.theme === "light" ? "light" : "dark";
    $("set-wrap").checked = !!c.word_wrap;
    $("set-autosave").checked = !!c.auto_save;
    ACCENT_HEX = c.accents || {};
    const box = $("set-accents");
    box.innerHTML = "";
    for (const [name] of Object.entries(ACCENT_HEX)) {
      const sw = document.createElement("button");
      sw.className = "swatch" + (name === c.accent ? " sel" : "");
      sw.title = name;
      sw.dataset.name = name;
      sw.onclick = () => saveConfig({ accent: name });
      box.appendChild(sw);
    }
    paintSwatches(c.accent);
  } catch (e) { /* bridge offline */ }
}

function paintSwatches(selected) {
  // swatches use the LIVE --accent for the current one; each shows its
  // own colour via a per-name lookup once we know the hexes — the
  // bridge sends labels, so we colour them with well-known hexes
  const HEX = { violet: "#8b5cf6", cyan: "#22d3ee", green: "#4ade80",
                orange: "#fb923c", rose: "#fb7185", blue: "#60a5fa" };
  document.querySelectorAll(".swatch").forEach(sw => {
    sw.style.background = HEX[sw.dataset.name] || "var(--accent)";
    sw.classList.toggle("sel", sw.dataset.name === selected);
  });
}

async function saveConfig(patch) {
  const r = await (await api("/api/config", {
    method: "POST", body: JSON.stringify(patch) })).json();
  if (r.ok) {
    const applied = r.applied ? Object.keys(r.applied) : [];
    toast("Saved: " + (applied.join(", ") || "?"));
    paintSwatches(patch.accent);
    poll();  // theme tokens re-stream → instant recolour
  } else {
    toast("Setting failed: " + (r.error || "?"));
  }
}

$("btn-settings").onclick = async () => {
  $("settings-overlay").classList.remove("hidden");
  await loadConfig();
};
$("settings-overlay").addEventListener("mousedown", (e) => {
  if (e.target.id === "settings-overlay")
    $("settings-overlay").classList.add("hidden");
});
$("set-theme").addEventListener("change", (e) =>
  saveConfig({ theme: e.target.value }));
$("set-wrap").addEventListener("change", (e) =>
  saveConfig({ word_wrap: e.target.checked }));
$("set-autosave").addEventListener("change", (e) =>
  saveConfig({ auto_save: e.target.checked }));
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    $("settings-overlay").classList.add("hidden");
  }
});

/* ---------- boot ---------- */
async function gitChipUpdate() {
  try {
    const r = await (await api("/api/git")).json();
    $("git-chip").textContent = r.ok
      ? `⎇ ${r.branch}${r.dirty ? " ●" + r.dirty : ""}` : "⎇ —";
  } catch (e) { /* bridge offline */ }
}
poll();
renderTree();
renderHighlight();
loadCommands();
loadConfig();
gitChipUpdate();
setInterval(poll, 1200);
setInterval(renderTree, 8000);
setInterval(gitChipUpdate, 6000);
