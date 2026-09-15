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
let bootstrapped = false;   // session restore runs once, after the
                            // first successful state snapshot

/* ---------- session (wave 7: the web face remembers) ---------- */
const scrollKey = (p) => "dxn1_scroll_" + p;

function rememberScroll() {
  if (!currentFile) return;
  localStorage.setItem(scrollKey(currentFile),
                       String($("editor").scrollTop));
}

function restoreScrollFor(path) {
  const v = parseInt(localStorage.getItem(scrollKey(path)) || "0", 10);
  if (v > 0) {
    // wait one frame — the textarea only grows after the value lands
    requestAnimationFrame(() => { $("editor").scrollTop = v; syncScroll(); });
  }
}

async function restoreSession() {
  if (currentFile || !(STATE.tabs || []).length) return;
  const saved = localStorage.getItem("dxn1_last_file");
  const tab = STATE.tabs.find(t => t.path === saved)
    || STATE.tabs.find(t => t.active) || STATE.tabs[0];
  if (!tab) return;
  await openFile(tab.path, true);
}

/* ---------- web-local preferences (wave 9: minimap, zen) ----------
   These live in localStorage — they are renderer preferences, not
   workspace config, so they never ride the bridge. */
function pref(key, val) {
  if (val === undefined) {
    return localStorage.getItem("dxn1_" + key) === "1";
  }
  localStorage.setItem("dxn1_" + key, val ? "1" : "0");
  return !!val;
}

function applyMini(on) {
  $("editor-wrap").classList.toggle("mini-on", !!on);
  const box = $("set-mini");
  if (box) box.checked = !!on;
  renderMinimap();
}

function applyZen(on) {
  document.body.classList.toggle("zen", !!on);
  const box = $("set-zen");
  if (box) box.checked = !!on;
  if (on) toast("Zen mode — Ctrl+Alt+Z to exit");
}

function applyWebPrefs() {
  applyMini(pref("minimap"));
  applyZen(pref("zen"));
}

/* ---------- minimap (wave 9) ----------
   A canvas overview: one dim bar per logical line, the viewport
   painted in the accent, click/drag to jump. Redrawn on rAF. */
let miniRaf = 0;

function miniWindow(ta, heightPx) {
  // shared math: which logical lines the minimap is showing
  const slot = 2;
  const edLH = parseFloat(getComputedStyle(ta).lineHeight) || 20;
  const lines = ta.value.split("\n");
  const totalSlots = lines.length * slot;
  let start = 0;
  if (totalSlots > heightPx) {
    const first = Math.floor(ta.scrollTop / edLH);
    const span = Math.ceil(heightPx / slot);
    const vis = Math.ceil(ta.clientHeight / edLH);
    start = Math.max(0, Math.min(lines.length - span,
                  first + Math.floor(vis / 2) - Math.floor(span / 2)));
  }
  return { slot, edLH, lines, start };
}

function renderMinimap() {
  if (!$("editor-wrap").classList.contains("mini-on")) return;
  cancelAnimationFrame(miniRaf);
  miniRaf = requestAnimationFrame(() => {
    const cv = $("minimap"), ta = $("editor");
    if (!cv.clientWidth || !cv.clientHeight) return;
    const dpr = window.devicePixelRatio || 1;
    const W = cv.clientWidth, H = cv.clientHeight;
    if (cv.width !== Math.round(W * dpr) ||
        cv.height !== Math.round(H * dpr)) {
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    }
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const { slot, edLH, lines, start } = miniWindow(ta, H);
    const root = getComputedStyle(document.documentElement);
    const acc = (root.getPropertyValue("--accent") || "").trim()
      || "#8b5cf6";
    ctx.fillStyle = "rgba(154,167,184,.5)";
    const shown = Math.min(lines.length - start, Math.ceil(H / slot));
    for (let i = 0; i < shown; i++) {
      const len = lines[start + i].replace(/\t/g, "    ").length;
      if (!len) continue;
      ctx.fillRect(5, i * slot, Math.min(W - 10, 1.5 + len * 1.15), 1.2);
    }
    const vTop = Math.max(0, (ta.scrollTop / edLH - start) * slot);
    const vH = Math.max(6, (ta.clientHeight / edLH) * slot);
    ctx.fillStyle = acc + "2e";
    ctx.fillRect(0, vTop, W, vH);
    ctx.fillStyle = acc;
    ctx.fillRect(0, vTop, 2, vH);
  });
}

function miniJump(e) {
  const cv = $("minimap"), ta = $("editor");
  const rect = cv.getBoundingClientRect();
  const { slot, edLH, lines, start } = miniWindow(ta, rect.height);
  const line = start + Math.floor((e.clientY - rect.top) / slot);
  ta.scrollTop = Math.max(0,
    Math.min(ta.scrollHeight, line * edLH - ta.clientHeight / 2.5));
  renderMinimap();
}

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
       `<span class="dot">●</span>` : "") +
      `<span class="x" title="Close tab (middle-click works too)">×<\/span>`;
    el.onclick = () => openFile(tb.path);
    el.onauxclick = (e) => {
      if (e.button === 1) { e.preventDefault(); closeTab(tb.path); }
    };
    el.querySelector(".x").onclick = (e) => {
      e.stopPropagation(); closeTab(tb.path);
    };
    bar.appendChild(el);
  }
}

function renderGutter() {
  const lines = $("editor").value.split("\n").length || 1;
  $("gutter").textContent = Array.from({ length: lines },
    (_, i) => i + 1).join("\n");
}

/* wave 8 — Ln/Col in the statusbar, like the desktop face */
function updatePos() {
  const el = $("st-pos");
  if (!currentFile) { el.textContent = ""; return; }
  const ta = $("editor");
  const upto = ta.value.slice(0, ta.selectionStart);
  const line = upto.split("\n").length;
  const col = ta.selectionStart - upto.lastIndexOf("\n");
  el.textContent = `Ln ${line}, Col ${col}`;
}

async function openFile(path, quiet = false) {
  const r = await (await api("/api/file?path=" + encodeURIComponent(path))).json();
  if (!r.ok) return toast("Open failed: " + (r.error || "?"));
  currentFile = r.file.path;
  $("editor").value = r.file.content;
  dirtyLocal = false;
  SNIP_SESS = null;   // a new file ends any hop session
  snipHint(false);
  $("st-file").textContent = currentFile;
  renderGutter();
  renderHighlight();
  renderTabs();
  updatePos();
  renderMinimap();
  loadSnippets();   // wave 10 — pack for the new language (cached)
  restoreScrollFor(currentFile);   // wave 7 — the scroll comes back
  localStorage.setItem("dxn1_last_file", currentFile);
  // tell the Tk side too — the file joins _buffers, so the tab bar
  // and the desktop app show the same open set (single source of truth)
  api("/api/open", { method: "POST", body: JSON.stringify({ path: r.file.path }) })
    .catch(() => {});
  if (!quiet) toast("Opened " + path.split("/").pop());
}

async function closeTab(path) {
  // web-local edits live only in the textarea until Ctrl+S — never
  // let a close throw them away without asking
  if (path === currentFile && dirtyLocal &&
      !confirm("Discard unsaved changes in " + path.split("/").pop() + "?"))
    return;
  const r = await (await api("/api/close", {
    method: "POST", body: JSON.stringify({ path }) })).json();
  if (!r.ok) return toast("Close failed: " + (r.error || "?"));
  toast("Closed " + path.split("/").pop());
  if (path === currentFile) {
    currentFile = null;
    dirtyLocal = false;
    $("editor").value = "";
    $("st-file").textContent = "";
    $("st-pos").textContent = "";
    localStorage.removeItem("dxn1_last_file");
    renderGutter(); renderHighlight(); renderTabs();
  }
  renderTree();
  // the desktop drains its mutation queue on its own cadence — wait
  // until the closed tab is REALLY gone before following the
  // desktop's activated tab (otherwise we re-open what we closed)
  for (let i = 0; i < 8; i++) {
    await poll();
    if (!(STATE.tabs || []).some(t => t.path === path)) break;
    await new Promise(res => setTimeout(res, 180));
  }
  if (!currentFile && (STATE.tabs || []).length) {
    const nxt = STATE.tabs.find(t => t.active)
      || STATE.tabs[STATE.tabs.length - 1];
    if (nxt) await openFile(nxt.path, true);
  }
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
  renderAgent();
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
    if (r.ok) {
      STATE = r; renderState();
      if (!bootstrapped) {
        bootstrapped = true;
        restoreSession();   // wave 7 — reload picks up where you left
      }
    }
  } catch (e) { /* bridge restarting — keep last frame */ }
}

/* ---------- command palette ---------- */
const WEB_CMDS = [
  { index: -1, label: "Web: toggle minimap", key: "",
    web: true,
    run: () => { const v = !pref("minimap");
                 pref("minimap", v); applyMini(v); } },
  { index: -2, label: "Web: toggle zen mode", key: "Ctrl+Alt+Z",
    web: true,
    run: () => { const v = !pref("zen");
                 pref("zen", v); applyZen(v); } },
];

/* ---------- snippets (wave 10) — same brain as the desktop ------
   The bridge serves snippets2's packs (builtins + the shared
   ~/.dxn1-studio/snippets.json). Expansion happens LOCALLY: Tab is
   zero-latency and works even if the bridge blinks mid-keystroke. */
let SNIPS = null, SNIPS_LANG = null, SNIP_CMDS = [];
let SNIP_SESS = null;   // active Tab-hop session (stops are absolute)

function snipHint(on) {   // statusbar hint: visible only while hopping
  $("st-snip").classList.toggle("hidden", !on);
}
let BASE_CMDS = WEB_CMDS;

async function loadSnippets() {
  const lang = currentFile ? langFor(currentFile) : null;
  if (!lang || lang === SNIPS_LANG) return;
  try {
    const r = await (await api("/api/snippets?lang=" +
      encodeURIComponent(lang))).json();
    if (r.ok) { SNIPS = r.snippets || []; SNIPS_LANG = lang;
                buildSnippetCmds(); }
  } catch (e) { /* bridge offline — Tab still indents normally */ }
}

function snipBuiltin(name) {
  const d = new Date();
  if (name === "DATE") return d.toISOString().slice(0, 10);
  if (name === "TIME")
    return String(d.getHours()).padStart(2, "0") + ":" +
           String(d.getMinutes()).padStart(2, "0");
  if (name === "FILENAME")
    return currentFile ? currentFile.split("/").pop() : "untitled";
  return "";   // CLIPBOARD needs clipboard-read permission — honest empty
}

// ${name:default} · ${name} · ${N} · $N · $$ — mirrors snippets2's
// TOKEN_RE. Returns {text, stops:[{s,e}]} with stops in appearance
// order; the caret lands on the first (typing replaces its default).
function snipExpand(body, indent) {
  const prepared = indent
    ? body.split("\n").map((l, ix) => ix && l ? indent + l : l)
          .join("\n")
    : body;
  let text = ""; const stops = [];
  for (let i = 0; i < prepared.length; ) {
    if (prepared[i] === "$") {
      const rest = prepared.slice(i);
      if (rest[1] === "$") { text += "$"; i += 2; continue; }
      let m = /^\$\{([A-Za-z_]\w*)(?::([^}\n]*))?\}/.exec(rest);
      if (m) {
        const def = m[2] !== undefined ? m[2] : m[1];
        if (def) stops.push({ s: text.length, e: text.length + def.length });
        text += def; i += m[0].length; continue;
      }
      m = /^\$\{(\d+)\}/.exec(rest) || /^\$(\d)/.exec(rest);
      if (m) { stops.push({ s: text.length, e: text.length });
               i += m[0].length; continue; }
      const bv = /^(FILENAME|DATE|TIME|CLIPBOARD)/.exec(rest);
      if (bv) { const v = snipBuiltin(bv[1]); text += v;
                i += bv[0].length; continue; }
    }
    text += prepared[i]; i++;
  }
  return { text, stops };
}

function insertSnippet(ta, prefix, body) {
  const s = ta.selectionStart, en = ta.selectionEnd;
  const before = ta.value.slice(0, s);
  const lineStart = before.lastIndexOf("\n") + 1;
  const indent = (/^[ \t]*/.exec(before.slice(lineStart)) || [""])[0];
  const { text, stops } = snipExpand(body, indent);
  const base = s - prefix.length;
  ta.value = before.slice(0, base) + text + ta.value.slice(en);
  const abs = stops.map(st =>
    ({ s: base + st.s, e: base + st.e, w: st.e - st.s }));
  if (abs.length) {
    ta.selectionStart = abs[0].s;
    ta.selectionEnd = abs[0].e;
  } else {
    ta.selectionStart = ta.selectionEnd = base + text.length;
  }
  // snippet session: Tab hops forward, Shift+Tab back (sequential
  // filling is exact — drift correction covers edits over stops)
  SNIP_SESS = abs.length > 1
    ? { stops: abs, idx: 0, drift: 0, len: ta.value.length }
    : null;
  snipHint(!!SNIP_SESS);
  dirtyLocal = true; renderHighlight(); renderGutter(); updatePos();
  renderMinimap();
  toast("✂ " + (prefix || "snippet"));
}

// hop to stop `to` (an index into SESS.stops) applying the drift
// the user introduced while filling earlier stops
function snipHop(ta, sess, to) {
  const st = sess.stops[to];
  // a stop we have LEFT before keeps its recorded absolute position
  // (drift moved past it); a never-left stop uses live drift
  const target = (st.pos !== undefined) ? st.pos : st.s + sess.drift;
  ta.selectionStart = target;
  ta.selectionEnd = target +
    (st.w !== undefined ? st.w : st.e - st.s);
  sess.idx = to;
}

// returns true if the Tab was consumed by an active snippet session
function snipSessionTab(ta, back) {
  const sess = SNIP_SESS;
  if (!sess) return false;
  const nxt = sess.idx + (back ? -1 : 1);
  if (nxt < 0) return true;              // stay on the first stop
  if (nxt >= sess.stops.length) {        // last stop — exit the
    const last = sess.stops[sess.idx];   // snippet like VS Code: the
    const end = (last.pos !== undefined // caret collapses at the end
                 ? last.pos             // of the last fill; another
                 : last.s + sess.drift) // Tab then indents cleanly
               + (last.w !== undefined ? last.w : last.e - last.s);
    ta.selectionStart = ta.selectionEnd = end;
    SNIP_SESS = null;
    snipHint(false);
    return true;
  }
  // EXACT drift: whatever the user did since the last hop shifted
  // every later stop by the textarea's length change (sequential
  // filling never edits past the stop being filled)
  // remember the fill width we are leaving so Shift+Tab re-selects
  // the user's text, not the original placeholder (caret strictly
  // inside the fill means real typing — an untouched re-forward
  // keeps the recorded width)
  const left = sess.stops[sess.idx];
  const fillStart = left.s + sess.drift;   // drift AT ARRIVAL
  if (ta.selectionStart > fillStart)
    left.w = ta.selectionStart - fillStart;
  left.pos = fillStart;                    // freeze the position
  sess.drift += ta.value.length - sess.len;
  sess.len = ta.value.length;
  snipHop(ta, sess, nxt);
  return true;
}

function snipFromPalette(prefix, body) {
  if (!currentFile) return toast("Open a file first");
  const ta = $("editor");
  ta.focus();
  insertSnippet(ta, "", body);   // nothing to strip — insert at caret
}

function buildSnippetCmds() {
  SNIP_CMDS = (SNIPS || []).map((s, ix) => ({
    index: -1000 - ix, web: true,
    label: "Snippet: " + s.prefix + "  →  " +
      (s.body.split("\n")[0] || "").slice(0, 42),
    run: () => snipFromPalette(s.prefix, s.body),
  }));
  CMDS = BASE_CMDS.concat(SNIP_CMDS);
}

async function loadCommands() {
  const r = await (await api("/api/commands")).json();
  BASE_CMDS = r.ok ? r.commands.concat(WEB_CMDS) : WEB_CMDS;
  CMDS = BASE_CMDS.concat(SNIP_CMDS);
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
  if (cmd.web) {           // renderer-local verbs — no bridge roundtrip
    cmd.run();
    return;
  }
  const r = await (await api("/api/command", {
    method: "POST", body: JSON.stringify({ index: cmd.index }),
  })).json();
  if (r.ok) {
    toast("▶ " + r.ran);
    // wrap/theme palette verbs change config on the desktop side —
    // re-pull it so the web editor follows instantly
    if (/wrap|theme/i.test(r.ran || "")) loadConfig();
  } else toast("Failed: " + (r.error || "?"));
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
  updatePos();
  renderMinimap();
});
["keyup", "click", "focus"].forEach(ev =>
  $("editor").addEventListener(ev, updatePos));
// wave 8 — never lose textarea-only edits to a careless reload
window.addEventListener("beforeunload", (e) => {
  if (dirtyLocal) { e.preventDefault(); e.returnValue = ""; }
});
let scrollSaveTimer = null;
$("editor").addEventListener("scroll", () => {
  syncScroll();
  renderMinimap();
  clearTimeout(scrollSaveTimer);          // wave 7 — debounce the save
  scrollSaveTimer = setTimeout(rememberScroll, 200);
});
// minimap interaction: click jumps, hold-and-drag scrubs
let miniScrubbing = false;
$("minimap").addEventListener("mousedown", (e) => {
  miniScrubbing = true; miniJump(e); e.preventDefault();
});
window.addEventListener("mousemove", (e) => {
  if (miniScrubbing) miniJump(e);
});
window.addEventListener("mouseup", () => { miniScrubbing = false; });
window.addEventListener("resize", renderMinimap);
$("editor").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveFile(); }
  if (e.key === "Tab") {  // session hop → snippet → real indent
    e.preventDefault();
    const ta = e.target, s = ta.selectionStart, en = ta.selectionEnd;
    if (snipSessionTab(ta, e.shiftKey)) { updatePos(); return; }
    const wm = SNIPS && s === en
      ? /([A-Za-z_]\w*)$/.exec(ta.value.slice(0, s)) : null;
    const snip = wm && SNIPS.find(x => x.prefix === wm[1]);
    if (snip) { insertSnippet(ta, wm[1], snip.body); return; }
    ta.value = ta.value.slice(0, s) + "    " + ta.value.slice(en);
    ta.selectionStart = ta.selectionEnd = s + 4;
    dirtyLocal = true; renderHighlight(); renderGutter();
  }
  if (e.key === "Escape") {   // end hop session, collapse leftover
    SNIP_SESS = null;         // selection so Tab cannot eat it
    snipHint(false);
    ta.selectionStart = ta.selectionEnd;
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
  if (e.ctrlKey && e.altKey && e.key.toLowerCase() === "z") {
    e.preventDefault();
    const v = !pref("zen"); pref("zen", v); applyZen(v);
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
function populateBranches(r) {
  const row = $("git-branch-row"), sel = $("git-branch-sel");
  const branches = r.branches || [];
  const cur = (r.branch || "").replace(" (fresh)", "");
  if (branches.length < 2) { row.style.display = "none"; return; }
  row.style.display = "";
  sel.innerHTML = branches.map(b =>
    `<option${b === cur ? " selected" : ""}>${esc(b)}</option>`).join("");
}

async function loadGit() {
  try {
    const r = await (await api("/api/git")).json();
    if (!r.ok) {
      $("git-branch").textContent = "not a git repo";
      $("git-branch-row").style.display = "none";
      $("git-files").innerHTML = "";
      $("git-log").innerHTML = "";
      return;
    }
    $("git-branch").innerHTML = `⎇ <b>${esc(r.branch)}</b>` +
      (r.dirty ? ` <span class="dot">● ${r.dirty} changed</span>` :
                 ` <span class="git-empty" style="display:inline">clean</span>`);
    populateBranches(r);
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

/* ---- diff view ---- */
async function openDiff() {
  $("diff-overlay").classList.remove("hidden");
  const body = $("diff-body");
  body.innerHTML = `<span class="dl-meta">diffing…</span>`;
  try {
    const r = await (await api("/api/diff")).json();
    if (!r.ok) {
      body.innerHTML = `<span class="dl-meta">${esc(r.error || "?")}</span>`;
      return;
    }
    body.innerHTML = r.diff.split("\n").map(line => {
      const safe = esc(line) || " ";
      if (line.startsWith("+++") || line.startsWith("---") ||
          line.startsWith("diff") || line.startsWith("index "))
        return `<span class="dl-meta">${safe}</span>`;
      if (line.startsWith("@@")) return `<span class="dl-hunk">${safe}</span>`;
      if (line.startsWith("+")) return `<span class="dl-add">${safe}</span>`;
      if (line.startsWith("-")) return `<span class="dl-del">${safe}</span>`;
      return safe;
    }).join("\n");
  } catch (e) {
    body.innerHTML = `<span class="dl-meta">bridge offline</span>`;
  }
}
$("git-diff").onclick = openDiff;
$("diff-close").onclick = () => $("diff-overlay").classList.add("hidden");
$("diff-overlay").addEventListener("mousedown", (e) => {
  if (e.target.id === "diff-overlay")
    $("diff-overlay").classList.add("hidden");
});

async function gitAction(action, extra = {}) {
  const r = await (await api("/api/git", {
    method: "POST",
    body: JSON.stringify({ action, ...extra }) })).json();
  if (r.ok) {
    toast(`${action} ✓ ${r.detail || ""}`.trim());
    loadGit();
    poll();
    renderTree();   // a checkout can change the whole tree
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
$("git-branch-go").onclick = async () => {
  const to = $("git-branch-sel").value;
  if (!to) return;
  if (!confirm("Switch to branch “" + to + "”?")) return;
  await gitAction("checkout", { branch: to });
};
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    ["git-overlay", "settings-overlay", "diff-overlay",
     "quickopen-overlay"].forEach(id => $(id).classList.add("hidden"));
  }
});

/* ---------- terminal input over the bridge ---------- */
let termHist = [];      // this session's commands (↑/↓ walks them)
let termHistPos = null;

async function termSubmit() {
  const inp = $("term-input");
  const cmd = inp.value.trim();
  if (!cmd) return;
  inp.value = "";
  termHist.push(cmd);
  if (termHist.length > 100) termHist.shift();
  termHistPos = null;
  const r = await (await api("/api/term", {
    method: "POST", body: JSON.stringify({ command: cmd }) })).json();
  if (r.ok) poll();
  else toast("Terminal: " + (r.error || "?"));
}
$("term-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") termSubmit();
  else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (!termHist.length) return;
    termHistPos = (termHistPos === null) ? termHist.length - 1
      : Math.max(0, termHistPos - 1);
    $("term-input").value = termHist[termHistPos];
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    if (termHistPos === null) return;
    termHistPos++;
    if (termHistPos >= termHist.length) {
      termHistPos = null;
      $("term-input").value = "";
    } else $("term-input").value = termHist[termHistPos];
  }
});

/* ---------- settings ---------- */
let ACCENT_HEX = {};

function applyWrap(on) {
  const ta = $("editor");
  ta.wrap = on ? "soft" : "off";
  $("editor-wrap").classList.toggle("wrap-on", !!on);
  renderMinimap();   // wrap changes the visual line count
}

async function loadConfig() {
  try {
    const r = await (await api("/api/config")).json();
    if (!r.ok) return;
    const c = r.config;
    $("set-theme").value = c.theme === "light" ? "light" : "dark";
    $("set-wrap").checked = !!c.word_wrap;
    $("set-autosave").checked = !!c.auto_save;
    applyWrap(!!c.word_wrap);   // wave 7 — wrap now actually wraps
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
    if ("word_wrap" in patch) applyWrap(!!patch.word_wrap);
    poll();  // theme tokens re-stream → instant recolour
  } else {
    toast("Setting failed: " + (r.error || "?"));
  }
}

$("btn-settings").onclick = async () => {
  $("settings-overlay").classList.remove("hidden");
  $("set-mini").checked = pref("minimap");
  $("set-zen").checked = pref("zen");
  await loadConfig();
};
$("set-mini").addEventListener("change", (e) => {
  pref("minimap", e.target.checked); applyMini(e.target.checked);
});
$("set-zen").addEventListener("change", (e) => {
  pref("zen", e.target.checked); applyZen(e.target.checked);
});
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

/* ---------- agents drawer ---------- */
let lastTranscriptLen = -1;

function renderAgent() {
  const a = STATE.agent || { busy: false, transcript: [] };
  $("agent-busy").classList.toggle("hidden", !a.busy);
  const t = a.transcript || [];
  if (t.length === lastTranscriptLen) return;
  lastTranscriptLen = t.length;
  const box = $("agent-transcript");
  box.innerHTML = t.map(m => {
    const cls = m.role === "user" ? "user" :
      (m.role === "system" ? "system" : "assistant");
    return `<div class="bubble ${cls}">${esc(m.text)}</div>`;
  }).join("") ||
    `<div class="bubble system">Ask anything — the agents share this
     workspace with the desktop app.</div>`;
  box.scrollTop = box.scrollHeight;
}

async function agentSend() {
  const inp = $("agent-input");
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = "";
  const r = await (await api("/api/agent", {
    method: "POST", body: JSON.stringify({ message: msg }) })).json();
  if (r.ok) { toast("◆ Agents: message sent"); poll(); }
  else toast("Agent failed: " + (r.error || "?"));
}

$("btn-agents").onclick = () => {
  const d = $("agent-drawer");
  d.classList.toggle("hidden");
  if (!d.classList.contains("hidden")) {
    lastTranscriptLen = -1;  // force re-render
    renderAgent();
    setTimeout(() => $("agent-input").focus(), 40);
  }
};
$("agent-send").onclick = agentSend;
$("agent-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") agentSend();
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
applyWebPrefs();   // wave 9 — minimap / zen come back from localStorage
loadCommands();
loadConfig();
gitChipUpdate();
setInterval(poll, 1200);
setInterval(renderTree, 8000);
setInterval(gitChipUpdate, 6000);
