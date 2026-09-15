// ============================================================
// DXN1 STUDIO 3 — the face's brain.
// Talks to the Python engine through window.dxn1 (Electron) or a
// demo virtual FS (browser / engine missing) — the UI never dies.
// ============================================================
"use strict";

/* ---------------- tiny dom helpers ---------------- */
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/&/g, "&amp;")
  .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ---------------- persistent prefs ---------------- */
const STORE = {
  get(k, d) { try { const v = localStorage.getItem("dxn3_" + k);
    return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("dxn3_" + k, JSON.stringify(v)); } catch {} },
};

/* ---------------- state ---------------- */
let FS = null;            // the face's filesystem client
let OPEN_TABS = [];       // [{path, kind:"file"|"scene", dirty}]
let ACTIVE = null;        // active tab path
let TREE = [];            // flat engine tree
let RECENTS = STORE.get("recents", []);
let SCENE_PATH = null;    // open scene path (game view)
let GAME = null;          // live Spark.Game
let SEL_ENT = null;
const VERSION = "3.0.01";

/* ============================================================
   ENGINE CLIENTS
   ============================================================ */
class DemoFS {
  /* browser / engine-missing mode: a small virtual FS in
     localStorage so every control still works. Honest: the
     statusbar says ENGINE demo. */
  constructor() {
    this.data = STORE.get("demo_fs", null);
    if (!this.data) {
      this.data = {};
      this.put("README.md",
        "# DXN1 STUDIO 3\n\nA beautiful studio for code and games.\n\n" +
        "- Electron face, Python brain\n- Spark 2D engine built in\n" +
        "- Press **F5** to play the playground scene\n\n" +
        "(engine offline — you are looking at the demo filesystem)\n");
      this.put("main.py", "def main():\n    print(\"hello from STUDIO 3\")\n\n\n"
        + "if __name__ == \"__main__\":\n    main()\n");
      this.put("scenes/playground.dxn1.json",
        JSON.stringify(Spark.demoScene(), null, 2));
      this.save();
    }
  }
  put(path, content) { this.data[path] = content; this.save(); }
  save() { STORE.set("demo_fs", this.data); }
  async request(cmd, args) {
    const ok = (result) => ({ ok: true, result });
    const bad = (error) => ({ ok: false, error });
    switch (cmd) {
      case "hello":
        return ok({ app: "DXN1 STUDIO 3", engine: "demo",
                    version: VERSION, workspace: "demo" });
      case "tree": {
        const seen = new Set();
        const tree = [];
        for (const p of Object.keys(this.data).sort()) {
          const parts = p.split("/");
          for (let i = 1; i < parts.length; i++) {
            const dir = parts.slice(0, i).join("/");
            if (!seen.has(dir)) {
              seen.add(dir);
              tree.push({ name: parts[i - 1], path: dir, dir: true });
            }
          }
          tree.push({ name: parts[parts.length - 1], path: p, dir: false });
        }
        return ok({ tree, count: tree.length });
      }
      case "read":
        return (args.path in this.data)
          ? ok({ path: args.path, content: this.data[args.path] })
          : bad("no such file");
      case "write":
        this.put(String(args.path), String(args.content || ""));
        return ok({ written: args.path });
      case "mkdir": return ok({ made: args.path });
      case "rename": {
        const from = args.from, to = args.to;
        if (!(from in this.data)) return bad("no such file");
        this.data[to] = this.data[from];
        delete this.data[from];
        this.save();
        return ok({ renamed: from, to });
      }
      case "delete":
        delete this.data[args.path];
        this.save();
        return ok({ deleted: args.path });
      case "scene_get":
        return (args.path in this.data)
          ? ok({ path: args.path,
                 scene: JSON.parse(this.data[args.path]) })
          : bad("no such scene");
      case "scene_save":
        this.put(String(args.path), JSON.stringify(args.scene, null, 2));
        return ok({ saved: args.path });
      default:
        return bad(`demo engine does not implement ${cmd}`);
    }
  }
}

class ElectronFS {
  async request(cmd, args) {
    if (!window.dxn1) return { ok: false, error: "no bridge" };
    return window.dxn1.request(cmd, args);
  }
}

async function api(cmd, args = {}) {
  const res = await FS.request(cmd, args);
  if (!res.ok) throw new Error(res.error || "engine error");
  return res.result;
}

/* ============================================================
   TOASTS + STATUS MESSAGE
   ============================================================ */
function toast(msg, kind = "info", ms = 2600) {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = msg;
  $("toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .25s";
    setTimeout(() => el.remove(), 260); }, ms);
}
function say(msg) { $("st-msg").textContent = msg; }

/* ============================================================
   FILE TREE
   ============================================================ */
async function loadTree() {
  try {
    const r = await api("tree", { depth: 3 });
    TREE = r.tree || [];
    renderTree();
  } catch (e) { say("engine: " + e.message); }
}

function buildHierarchy(flat) {
  const root = { name: "", path: "", dir: true, kids: new Map() };
  for (const item of flat) {
    const parts = item.path.split("/");
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const p = parts.slice(0, i + 1).join("/");
      if (!node.kids.has(p)) {
        node.kids.set(p, { name: parts[i], path: p, dir: true,
                           kids: new Map(), open: STORE.get("open_" + p, true) });
      }
      node = node.kids.get(p);
    }
    node.kids.set(item.path, { name: item.name, path: item.path,
                               dir: item.dir, kids: new Map(), open: false });
  }
  return root;
}

function renderTree() {
  const host = $("tree");
  host.innerHTML = "";
  if (!TREE.length) {
    host.innerHTML = `<div class="panel-note">No folder yet — use
      <b>Open Folder</b> on the welcome screen.</div>`;
    return;
  }
  const root = buildHierarchy(TREE);
  const addKids = (node, parent, depth) => {
    for (const kid of [...node.kids.values()].sort((a, b) =>
        (b.dir - a.dir) || a.name.localeCompare(b.name))) {
      if (kid.dir && !kid.kids.size) continue;
      parent.appendChild(treeRow(kid, depth));
      if (kid.dir && kid.open) addKids(kid, parent, depth + 1);
    }
  };
  addKids(root, host, 0);
}

function treeRow(item, depth) {
  const el = document.createElement("div");
  el.className = "tree-item" +
    (item.dir ? (item.open ? " open" : "") : (ACTIVE === item.path ? " active" : ""));
  el.style.paddingLeft = (9 + depth * 14) + "px";
  el.innerHTML = `<span class="ico ${item.dir ? "dir" : ""}">` +
    (item.dir ? (item.open ? "▾" : "▸")
      : "·") + `</span><span class="nm">${esc(item.name)}</span>` +
    (item.dir ? "" : `<span class="act">` +
      `<button data-a="ren" title="Rename">⋈</button>` +
      `<button class="danger" data-a="del" title="Delete">✕</button></span>`);
  el.onclick = async (e) => {
    if (e.target.dataset.a) return;
    if (item.dir) {
      item.open = !item.open;
      STORE.set("open_" + item.path, item.open);
      renderTree();
    } else openPath(item.path);
  };
  const ren = el.querySelector('[data-a="ren"]');
  if (ren) ren.onclick = (e) => { e.stopPropagation(); renamePath(item.path); };
  const del = el.querySelector('[data-a="del"]');
  if (del) del.onclick = (e) => { e.stopPropagation(); deletePath(item.path); };
  el.oncontextmenu = (e) => {
    e.preventDefault();
    ctxMenu(e.clientX, e.clientY, [
      { label: "Open", run: () => item.dir || openPath(item.path) },
      { label: "Rename", run: () => renamePath(item.path) },
      { label: "Delete", danger: true, run: () => deletePath(item.path) },
    ]);
  };
  return el;
}

async function openPath(path) {
  if (/\.(dxn1\.json)$/i.test(path)) return openScene(path);
  try {
    const r = await api("read", { path });
    OPEN_TABS = OPEN_TABS.filter((t) => t.path !== path);
    OPEN_TABS.push({ path, kind: "file", dirty: false });
    ACTIVE = path;
    $("editor").value = r.content;
    showView("editor");
    renderTabs(); renderHighlight(); renderGutter(); updatePos();
    addRecent(path);
    say("opened " + path);
  } catch (e) { toast("Open failed: " + e.message, "err"); }
}

async function saveActive() {
  const tab = OPEN_TABS.find((t) => t.path === ACTIVE);
  if (!tab) return toast("No file open", "err");
  try {
    if (tab.kind === "scene" && SCENE_PATH === tab.path) {
      await saveScene();
    } else {
      await api("write", { path: tab.path, content: $("editor").value });
    }
    tab.dirty = false;
    renderTabs();
    toast("Saved " + tab.path.split("/").pop(), "ok", 1600);
  } catch (e) { toast("Save failed: " + e.message, "err"); }
}

async function renamePath(path) {
  const to = prompt("Rename to:", path);
  if (!to || to === path) return;
  try {
    await api("rename", { from: path, to });
    OPEN_TABS = OPEN_TABS.map((t) => t.path === path ? { ...t, path: to } : t);
    if (ACTIVE === path) ACTIVE = to;
    await loadTree();
    say("renamed to " + to);
  } catch (e) { toast("Rename failed: " + e.message, "err"); }
}

async function deletePath(path) {
  if (!confirm("Delete " + path + "?")) return;
  try {
    await api("delete", { path });
    OPEN_TABS = OPEN_TABS.filter((t) => t.path !== path);
    if (ACTIVE === path) { ACTIVE = OPEN_TABS[0]?.path || null; ACTIVE ? openPath(ACTIVE) : showView("welcome"); }
    await loadTree();
    renderTabs();
    toast("Deleted " + path, "ok");
  } catch (e) { toast("Delete failed: " + e.message, "err"); }
}

async function newFile() {
  const path = prompt("New file path:", "untitled.py");
  if (!path) return;
  try {
    await api("write", { path, content: "" });
    await loadTree();
    openPath(path);
  } catch (e) { toast("Create failed: " + e.message, "err"); }
}

async function newFolder() {
  const path = prompt("New folder path:", "src");
  if (!path) return;
  try { await api("mkdir", { path }); await loadTree(); }
  catch (e) { toast("Create failed: " + e.message, "err"); }
}

function addRecent(path) {
  RECENTS = [path, ...RECENTS.filter((p) => p !== path)].slice(0, 6);
  STORE.set("recents", RECENTS);
  renderRecents();
}

/* ============================================================
   TABS + EDITOR
   ============================================================ */
function renderTabs() {
  const bar = $("tabstrip");
  bar.innerHTML = "";
  for (const t of OPEN_TABS) {
    const el = document.createElement("div");
    el.className = "tab" + (t.path === ACTIVE ? " active" : "");
    el.setAttribute("role", "tab");
    el.innerHTML = `<span>${esc(t.path.split("/").pop())}</span>` +
      (t.dirty ? `<span class="dot">●</span>` : "") +
      `<span class="x" title="Close">✕</span>`;
    el.onclick = (e) => {
      if (e.target.classList.contains("x")) return closeTab(t.path);
      if (t.kind === "scene") openScene(t.path);
      else openPath(t.path);
    };
    bar.appendChild(el);
  }
  $("st-file").textContent = ACTIVE || "";
}

async function closeTab(path) {
  const tab = OPEN_TABS.find((t) => t.path === path);
  if (tab?.dirty && !confirm("Discard unsaved changes in " + path + "?")) return;
  if (tab?.kind === "scene" && GAME) stopGame();
  OPEN_TABS = OPEN_TABS.filter((t) => t.path !== path);
  if (ACTIVE === path) {
    ACTIVE = OPEN_TABS[OPEN_TABS.length - 1]?.path || null;
    if (ACTIVE) {
      const nxt = OPEN_TABS[OPEN_TABS.length - 1];
      nxt.kind === "scene" ? openScene(ACTIVE) : openPath(ACTIVE);
      return;
    }
    showView("welcome");
  }
  renderTabs();
}

function langFor(path) {
  const ext = (path.split(".").pop() || "").toLowerCase();
  if (ext === "py") return "py";
  if (["js", "ts", "jsx", "tsx", "mjs"].includes(ext)) return "js";
  if (ext === "json") return "json";
  if (["md", "markdown"].includes(ext)) return "md";
  return "txt";
}

const PY_KW = "def|class|return|if|elif|else|for|while|import|from|as|with|try|except|finally|raise|lambda|pass|break|continue|and|or|not|in|is|None|True|False|global|nonlocal|yield|async|await|assert|del|match|case";
const JS_KW = "function|const|let|var|return|if|else|for|while|do|switch|case|break|continue|new|class|extends|super|this|typeof|instanceof|null|undefined|true|false|import|export|from|as|async|await|try|catch|finally|throw|yield|static|get|set|delete|void";

function highlight(src, lang) {
  const store = [];
  const keep = (html) => {
    store.push(html);
    return `\u0000${store.length - 1}\u0000`;
  };
  let out = esc(src);
  const sub = (re, cls) => {
    out = out.replace(re, (m) => keep(`<span class="tok-${cls}">${m}</span>`));
  };
  sub(/&quot;[^&]*?&quot;|&#39;[^&]*?&#39;|`[^`]*?`/g, "str");
  if (lang === "py") sub(/#[^\n]*/g, "com");
  if (lang === "js") sub(/\/\/[^\n]*/g, "com");
  if (lang === "py") sub(new RegExp(`\\b(?:${PY_KW})\\b`, "g"), "kw");
  if (lang === "js") sub(new RegExp(`\\b(?:${JS_KW})\\b`, "g"), "kw");
  if (lang === "json") sub(/\b(true|false|null)\b/g, "kw");
  sub(/\b\d+(\.\d+)?\b/g, "num");
  sub(/@[\w.]+/g, "dec");
  sub(/\b([a-zA-Z_]\w*)\(/g, (m, f) =>
    keep(`<span class="tok-fn">${f}</span>(`));
  if (lang === "md") {
    sub(/^#{1,6} .*$/gm, "kw");
    sub(/\*\*[^*]+\*\*/g, "fn");
  }
  out = out.replace(/\u0000(\d+)\u0000/g, (_, i) => store[Number(i)]);
  return out;
}

function renderHighlight() {
  const src = $("editor").value;
  const lang = ACTIVE ? langFor(ACTIVE) : "txt";
  $("highlight").innerHTML = highlight(src, lang) + "\n";
}

function renderGutter() {
  const n = $("editor").value.split("\n").length || 1;
  $("gutter").textContent = Array.from({ length: n }, (_, i) => i + 1).join("\n");
}

function updatePos() {
  const ta = $("editor");
  if (!ACTIVE) { $("st-pos").textContent = ""; return; }
  const upto = ta.value.slice(0, ta.selectionStart);
  const line = upto.split("\n").length;
  const col = ta.selectionStart - upto.lastIndexOf("\n");
  $("st-pos").textContent = `Ln ${line}, Col ${col}`;
}

function showView(name) {
  for (const v of ["welcome", "editor", "game"]) {
    $(v + "-view").classList.toggle("active", v === name);
  }
}

/* ============================================================
   SPARK INTEGRATION — scenes, play, inspector
   ============================================================ */
async function openScene(path) {
  try {
    const r = await api("scene_get", { path });
    SCENE_PATH = path;
    OPEN_TABS = OPEN_TABS.filter((t) => t.path !== path);
    OPEN_TABS.push({ path, kind: "scene", dirty: false });
    ACTIVE = path;
    showView("game");
    $("scene-name").textContent = path.split("/").pop();
    renderTabs();
    renderSceneDock(r.scene);
    buildGame(r.scene);
    addRecent(path);
    say("scene " + path + " — F5 to play");
  } catch (e) { toast("Scene failed: " + e.message, "err"); }
}

function buildGame(scene) {
  if (GAME) GAME.stop();
  GAME = new Spark.Game($("game-canvas"), scene, {
    onScore: (s) => say("score " + s),
    onStop: () => {
      $("btn-play").classList.remove("running");
      $("btn-play").textContent = "▶";
    },
  });
  GAME.selected = SEL_ENT;
  wireSceneEditing();
  renderEntityList();
}

let SCENE_EDIT_WIRED = false;
function wireSceneEditing() {
  if (SCENE_EDIT_WIRED) return;
  SCENE_EDIT_WIRED = true;
  const cv = $("game-canvas");
  let dragging = null;
  cv.addEventListener("mousedown", (e) => {
    if (!GAME || GAME.running) return;   // editing is an EDITOR power
    const w = GAME.screenToWorld(e.clientX, e.clientY);
    const ent = GAME.entityAt(w.x, w.y);
    SEL_ENT = ent;
    GAME.selected = ent;
    if (ent) {
      dragging = { ent, dx: w.x - ent.x, dy: w.y - ent.y };
      cv.setPointerCapture(e.pointerId);
    }
    renderEntityList(); renderInspector();
  });
  cv.addEventListener("mousemove", (e) => {
    if (!dragging || !GAME || GAME.running) return;
    const w = GAME.screenToWorld(e.clientX, e.clientY);
    dragging.ent.x = Math.round(w.x - dragging.dx);
    dragging.ent.y = Math.round(w.y - dragging.dy);
    markSceneDirty();
    renderInspector();                    // live numbers while dragging
  });
  cv.addEventListener("mouseup", () => { dragging = null; });
}

function renderSceneDock(scene) {
  // entity list + inspector for the NEW scene
  SEL_ENT = scene.entities.find((e) => e.tag === "player") ||
            scene.entities[0] || null;
  renderEntityList();
  renderInspector();
}

function renderEntityList() {
  const host = $("entity-list");
  host.innerHTML = "";
  if (!GAME) return;
  for (const e of GAME.scene.entities) {
    const el = document.createElement("div");
    el.className = "ent-item" + (SEL_ENT === e ? " sel" : "");
    el.innerHTML = `<span class="sw" style="background:${esc(e.color)}"></span>` +
      `<span>${esc(e.name)}</span>` +
      (e.tag ? `<span style="margin-left:auto;font-size:10px;color:var(--text3)">${esc(e.tag)}</span>` : "");
    el.onclick = () => { SEL_ENT = e; GAME.selected = e;
      renderEntityList(); renderInspector(); };
    host.appendChild(el);
  }
}

function renderInspector() {
  const host = $("inspector");
  host.innerHTML = "";
  if (!SEL_ENT) { host.innerHTML = `<div class="panel-note">click an entity on the canvas — drag to move</div>`; return; }
  const e = SEL_ENT;
  const row = (label, input) => {
    const r = document.createElement("div");
    r.className = "insp-row";
    r.innerHTML = `<label>${label}</label>`;
    r.appendChild(input);
    host.appendChild(r);
    return input;
  };
  const text = (val, on, type = "text") => {
    const i = document.createElement("input");
    i.type = type; i.value = val; i.spellcheck = false;
    i.oninput = () => { on(i.value); markSceneDirty(); };
    return i;
  };
  const num = (val, on) => text(String(val), (v) => on(Number(v) || 0), "number");
  row("name", text(e.name, (v) => { e.name = v; renderEntityList(); }));
  row("x", num(e.x, (v) => e.x = v));
  row("y", num(e.y, (v) => e.y = v));
  row("w", num(e.w, (v) => e.w = v));
  row("h", num(e.h, (v) => e.h = v));
  const color = document.createElement("input");
  color.type = "color"; color.value = e.color.startsWith("#") ? e.color : "#8b5cf6";
  color.className = "insp-color";
  color.oninput = () => { e.color = color.value; renderEntityList(); markSceneDirty(); };
  row("color", color);
  const sel = document.createElement("select");
  for (const s of ["rect", "circle"]) {
    const o = document.createElement("option");
    o.value = o.textContent = s; if (e.shape === s) o.selected = true;
    sel.appendChild(o);
  }
  sel.onchange = () => { e.shape = sel.value; markSceneDirty(); };
  row("shape", sel);
  const ctl = document.createElement("select");
  for (const s of ["none", "platformer"]) {
    const o = document.createElement("option");
    o.value = o.textContent = s; if (e.controls === s) o.selected = true;
    ctl.appendChild(o);
  }
  ctl.onchange = () => { e.controls = ctl.value; markSceneDirty(); };
  row("controls", ctl);
  const solid = document.createElement("input");
  solid.type = "checkbox"; solid.checked = !!e.solid; solid.className = "insp-check";
  solid.onchange = () => { e.solid = solid.checked; markSceneDirty(); };
  row("solid", solid);
  row("tag", text(e.tag || "", (v) => e.tag = v));
}

function markSceneDirty() {
  const tab = OPEN_TABS.find((t) => t.path === SCENE_PATH);
  if (tab) { tab.dirty = true; renderTabs(); }
}

async function saveScene() {
  if (!GAME || !SCENE_PATH) return toast("No scene open", "err");
  try {
    await api("scene_save", { path: SCENE_PATH, scene: GAME.scene });
    const tab = OPEN_TABS.find((t) => t.path === SCENE_PATH);
    if (tab) tab.dirty = false;
    renderTabs();
    toast("Scene saved", "ok", 1600);
  } catch (e) { toast("Save failed: " + e.message, "err"); }
}

function playScene() {
  if (!GAME) {
    // nothing open — play the demo scene directly (never a dead button)
    SCENE_PATH = SCENE_PATH || "scenes/playground.dxn1.json";
    const scene = Spark.demoScene();
    showView("game");
    $("scene-name").textContent = "playground (demo)";
    buildGame(scene);
  }
  if (GAME.running) return stopGame();
  SEL_ENT = null; GAME.selected = null;
  renderEntityList();
  GAME.start();
  $("btn-play").classList.add("running");
  $("btn-play").textContent = "■";
  say("playing " + (GAME.scene.name || "scene") + " — arrows/WASD + space");
}

function stopGame() {
  if (GAME) GAME.stop();
  $("btn-play").classList.remove("running");
  $("btn-play").textContent = "▶";
}

async function newScene() {
  const name = prompt("Scene name:", "my-game");
  if (!name) return;
  const path = `scenes/${name}.dxn1.json`;
  const scene = Spark.demoScene();
  scene.name = name;
  try {
    await api("scene_save", { path, scene });
    await loadTree();
    openScene(path);
  } catch (e) { toast("Create failed: " + e.message, "err"); }
}

async function openSceneList() {
  const host = $("scene-list");
  host.innerHTML = "";
  try {
    const r = await api("tree", { depth: 3 });
    const scenes = (r.tree || []).filter((t) => !t.dir && /\.dxn1\.json$/.test(t.path));
    if (!scenes.length) {
      host.innerHTML = `<div class="panel-note">no scenes yet — create one from the welcome screen</div>`;
      return;
    }
    for (const s of scenes) {
      const el = document.createElement("div");
      el.className = "scene-item";
      el.innerHTML = `<span class="ico">▶</span><span>${esc(s.name)}</span>`;
      el.onclick = () => openScene(s.path);
      host.appendChild(el);
    }
  } catch {}
}

/* ============================================================
   SEARCH (across files)
   ============================================================ */
async function runSearch(q) {
  const host = $("search-results");
  host.innerHTML = "";
  if (!q || q.length < 2) return;
  try {
    const r = await api("tree", { depth: 4 });
    const files = (r.tree || []).filter((t) => !t.dir);
    const hits = [];
    for (const f of files.slice(0, 200)) {
      if (hits.length > 40) break;
      try {
        const c = await api("read", { path: f.path });
        const lines = c.content.split("\n");
        for (let i = 0; i < lines.length && hits.length <= 40; i++) {
          const at = lines[i].toLowerCase().indexOf(q.toLowerCase());
          if (at >= 0) {
            hits.push({ path: f.path, line: i + 1, text: lines[i] });
            if (hits.length > 40) break;
          }
        }
      } catch {}
    }
    for (const h of hits) {
      const el = document.createElement("div");
      el.className = "sr-item";
      const marked = esc(h.text.trim().slice(0, 120))
        .replace(new RegExp(esc(q).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"),
                 (m) => `<b>${m}</b>`);
      el.innerHTML = `<div class="p">${esc(h.path)}:${h.line}</div>` +
                     `<div class="l">${marked}</div>`;
      el.onclick = () => openPath(h.path);
      host.appendChild(el);
    }
    say(`${hits.length} result${hits.length === 1 ? "" : "s"} for “${q}”`);
  } catch (e) { say("search failed: " + e.message); }
}

/* ============================================================
   COMMAND PALETTE
   ============================================================ */
const COMMANDS = [
  { ico: "▶", label: "Play scene", key: "F5", run: () => playScene() },
  { ico: "■", label: "Stop scene", run: () => stopGame() },
  { ico: "＋", label: "New file", run: () => newFile() },
  { ico: "⊞", label: "New folder", run: () => newFolder() },
  { ico: "▶", label: "New game scene (Spark)", run: () => newScene() },
  { ico: "⤓", label: "Save", key: "Ctrl+S", run: () => saveActive() },
  { ico: "⌂", label: "Open folder…", run: () => openFolder() },
  { ico: "⌕", label: "Search in project", key: "Ctrl+Shift+F",
    run: () => { switchPanel("search"); $("search-input").focus(); } },
  { ico: "◫", label: "Toggle terminal", key: "Ctrl+`",
    run: () => $("dock").classList.toggle("collapsed") },
  { ico: "◐", label: "Toggle theme",
    run: () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark") },
  { ico: "⇥", label: "Toggle word wrap", run: () => {
      const on = !$("editor-stack").classList.contains("wrap-on");
      $("editor-stack").classList.toggle("wrap-on", on);
      STORE.set("wrap", on); $("set-wrap").checked = on; } },
  { ico: "✕", label: "Close tab", key: "Ctrl+W", run: () => ACTIVE && closeTab(ACTIVE) },
  { ico: "⌗", label: "About DXN1 STUDIO 3", run: () =>
      toast(`DXN1 STUDIO 3 — v${VERSION} · Electron face · Python brain · Spark 2D inside`, "info", 5000) },
];

let PAL_SEL = 0;
let PAL_MODE = "cmd";   // cmd | file

function palOpen(mode = "cmd") {
  PAL_MODE = mode;
  $("overlay").classList.remove("hidden");
  const inp = $("palette-input");
  inp.value = "";
  PAL_SEL = 0;
  palRender("");
  setTimeout(() => inp.focus(), 20);
}

function palClose() { $("overlay").classList.add("hidden"); }

function palItems(q) {
  if (PAL_MODE === "file") {
    const files = TREE.filter((t) => !t.dir)
      .map((t) => ({ ico: "·", label: t.path, run: () => openPath(t.path) }));
    return fuzzy(files, q);
  }
  const cmds = fuzzy(COMMANDS.map((c) => ({ ...c, key: c.key || "" })), q);
  if (!q) return cmds;
  const files = TREE.filter((t) => !t.dir)
    .map((t) => ({ ico: "·", label: t.path, run: () => openPath(t.path) }));
  return [...cmds, ...fuzzy(files, q).slice(0, 5)];
}

function fuzzy(items, q) {
  if (!q) return items.slice(0, 30);
  const ql = q.toLowerCase();
  return items.filter((it) => it.label.toLowerCase().includes(ql)).slice(0, 30);
}

function palRender(q) {
  const host = $("palette-list");
  const items = palItems(q);
  host.innerHTML = "";
  PAL_SEL = Math.min(PAL_SEL, Math.max(0, items.length - 1));
  items.forEach((it, i) => {
    const el = document.createElement("div");
    el.className = "pal-item" + (i === PAL_SEL ? " sel" : "");
    el.innerHTML = `<span class="ico">${it.ico || "·"}</span>` +
      `<span>${esc(it.label)}</span>` + (it.key ? `<kbd>${it.key}</kbd>` : "");
    el.onclick = () => { palClose(); it.run(); };
    host.appendChild(el);
  });
}

function palRun() {
  const items = palItems($("palette-input").value);
  const it = items[PAL_SEL];
  if (it) { palClose(); it.run(); }
}

/* ============================================================
   TERMINAL
   ============================================================ */
function termPrint(text) {
  const out = $("term-out");
  out.textContent += text + "\n";
  out.scrollTop = out.scrollHeight;
}

const TERM_VERBS = {
  help: () => termPrint(
    "verbs: help · clear · ls · cat <file> · new <file> · rm <file>\n" +
    "       play [scene] · theme · accent <name> · about · date · echo <text>"),
  clear: () => { $("term-out").textContent = ""; },
  ls: () => termPrint(TREE.filter((t) => !t.dir).map((t) => t.path).join("\n") || "(empty)"),
  cat: (a) => api("read", { path: a[0] }).then((r) => termPrint(r.content)).catch((e) => termPrint("cat: " + e.message)),
  new: (a) => a[0] ? api("write", { path: a[0], content: "" })
    .then(() => loadTree()).then(() => termPrint("created " + a[0]))
    .catch((e) => termPrint("new: " + e.message)) : termPrint("usage: new <file>"),
  rm: (a) => a[0] ? api("delete", { path: a[0] }).then(() => loadTree())
    .then(() => termPrint("removed " + a[0]))
    .catch((e) => termPrint("rm: " + e.message)) : termPrint("usage: rm <file>"),
  play: (a) => a[0] ? openScene(a[0]).then(playScene) : playScene(),
  theme: () => { const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(t); termPrint("theme: " + t); },
  accent: (a) => { if (["violet", "cyan", "emerald", "amber", "rose"].includes(a[0])) {
    setAccent(a[0]); termPrint("accent: " + a[0]); } else termPrint("accents: violet cyan emerald amber rose"); },
  about: () => termPrint(`DXN1 STUDIO 3 v${VERSION} — Electron face · Python brain · Spark 2D engine`),
  date: () => termPrint(new Date().toString()),
  echo: (a) => termPrint(a.join(" ")),
};

async function termSubmit() {
  const inp = $("term-in");
  const line = inp.value.trim();
  inp.value = "";
  if (!line) return;
  termPrint("dxn1 ❯ " + line);
  const [verb, ...args] = line.split(/\s+/);
  const fn = TERM_VERBS[verb];
  if (fn) fn(args);
  else termPrint(`unknown verb: ${verb} — try help`);
}

/* ============================================================
   SETTINGS (theme / accent / editor)
   ============================================================ */
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  STORE.set("theme", t);
  document.querySelectorAll("#set-themes .seg")
    .forEach((b) => b.classList.toggle("active", b.dataset.theme === t));
}

function setAccent(a) {
  document.documentElement.dataset.accent = a;
  STORE.set("accent", a);
  document.querySelectorAll(".accent-dot")
    .forEach((b) => b.classList.toggle("active", b.dataset.accent === a));
}

function setFontSize(px) {
  document.documentElement.style.setProperty("--fs-editor", px + "px");
  STORE.set("fs", px);
  document.querySelectorAll("[data-fs]")
    .forEach((b) => b.classList.toggle("active", b.dataset.fs === String(px)));
  renderGutter();
}

/* ============================================================
   PANELS / WELCOME / WINDOW CHROME
   ============================================================ */
function switchPanel(name) {
  document.querySelectorAll(".rail-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.panel === name));
  document.querySelectorAll("#sidebar .panel").forEach((p) =>
    p.classList.toggle("active", p.id === "panel-" + name));
  if (name === "game") openSceneList();
  STORE.set("panel", name);
}

function renderRecents() {
  const host = $("hero-recents");
  host.innerHTML = "";
  for (const p of RECENTS) {
    const b = document.createElement("button");
    b.textContent = p;
    b.onclick = () => openPath(p);
    host.appendChild(b);
  }
}

async function openFolder() {
  if (window.dxn1?.pickFolder) {
    const dir = await window.dxn1.pickFolder({ title: "Open project folder" });
    if (dir) {
      await api("write", { path: ".dxn3-workspace", content: dir });  // marker (harmless)
      toast("Folder: " + dir.split(/[\\/]/).pop(), "ok");
      // the engine holds the workspace for this session; a full
      // workspace-switch lands with the engine sprint (tomorrow)
      await loadTree();
    }
  } else {
    toast("Folder picking needs the desktop app — demo mode uses its virtual files", "info", 4000);
  }
}

function ctxMenu(x, y, items) {
  const m = $("ctxmenu");
  m.innerHTML = "";
  for (const it of items) {
    if (it === "-") { const s = document.createElement("div"); s.className = "ctx-sep"; m.appendChild(s); continue; }
    const b = document.createElement("button");
    b.className = "ctx-item" + (it.danger ? " danger" : "");
    b.textContent = it.label;
    b.onclick = () => { m.classList.add("hidden"); it.run(); };
    m.appendChild(b);
  }
  m.classList.remove("hidden");
  const r = m.getBoundingClientRect();
  m.style.left = Math.min(x, innerWidth - r.width - 8) + "px";
  m.style.top = Math.min(y, innerHeight - r.height - 8) + "px";
}

/* ============================================================
   WIRING
   ============================================================ */
function wire() {
  // window chrome
  $("win-min").onclick = () => window.dxn1?.win("min");
  $("win-max").onclick = () => window.dxn1?.win("max");
  $("win-close").onclick = () => window.dxn1?.win("close");

  // titlebar
  $("command-bar").onclick = () => palOpen("cmd");
  $("btn-play").onclick = () => playScene();
  $("project-chip").onclick = () => openFolder();

  // rail
  document.querySelectorAll(".rail-btn").forEach((b) =>
    b.onclick = () => switchPanel(b.dataset.panel));

  // explorer
  $("btn-newfile").onclick = newFile;
  $("btn-newfolder").onclick = newFolder;
  $("btn-refresh").onclick = loadTree;

  // editor
  const ed = $("editor");
  ed.addEventListener("input", () => {
    renderHighlight(); renderGutter(); updatePos();
    const tab = OPEN_TABS.find((t) => t.path === ACTIVE);
    if (tab && !tab.dirty) { tab.dirty = true; renderTabs(); }
  });
  ed.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {                    // 2-space indent, always ours
      e.preventDefault();
      const s = ed.selectionStart, epos = ed.selectionEnd;
      ed.setRangeText("  ", s, epos, "end");
      renderHighlight(); renderGutter();
    }
  });
  ed.addEventListener("keyup", updatePos);
  ed.addEventListener("click", updatePos);

  // scene dock
  $("scene-save").onclick = saveScene;

  // search
  let searchT = 0;
  $("search-input").addEventListener("input", (e) => {
    clearTimeout(searchT);
    searchT = setTimeout(() => runSearch(e.target.value), 240);
  });

  // terminal
  $("term-in").addEventListener("keydown", (e) => {
    if (e.key === "Enter") termSubmit();
  });

  // palette
  $("palette-input").addEventListener("input", (e) => { PAL_SEL = 0; palRender(e.target.value); });
  $("palette-input").addEventListener("keydown", (e) => {
    const n = palItems($("palette-input").value).length;
    if (e.key === "ArrowDown") { e.preventDefault(); PAL_SEL = (PAL_SEL + 1) % n; palRender($("palette-input").value); }
    else if (e.key === "ArrowUp") { e.preventDefault(); PAL_SEL = (PAL_SEL - 1 + n) % n; palRender($("palette-input").value); }
    else if (e.key === "Enter") { e.preventDefault(); palRun(); }
    else if (e.key === "Escape") palClose();
  });
  $("overlay").addEventListener("mousedown", (e) => {
    if (e.target.id === "overlay") palClose();
  });

  // settings
  $("set-themes").addEventListener("click", (e) => {
    const t = e.target.dataset.theme; if (t) setTheme(t);
  });
  const accents = ["violet", "cyan", "emerald", "amber", "rose"];
  const accRow = $("set-accents");
  for (const a of accents) {
    const d = document.createElement("button");
    d.className = "accent-dot";
    d.dataset.accent = a;
    d.title = a;
    d.style.background = `linear-gradient(135deg, ${
      { violet: "#8b5cf6", cyan: "#22d3ee", emerald: "#34d399",
        amber: "#fbbf24", rose: "#fb7185" }[a]}, var(--accent2))`;
    d.onclick = () => setAccent(a);
    accRow.appendChild(d);
  }
  $("set-wrap").onchange = (e) => {
    $("editor-stack").classList.toggle("wrap-on", e.target.checked);
    STORE.set("wrap", e.target.checked);
  };
  document.querySelectorAll("[data-fs]").forEach((b) =>
    b.onclick = () => setFontSize(Number(b.dataset.fs)));

  // welcome
  $("hero-open").onclick = openFolder;
  $("hero-scene").onclick = newScene;
  $("hero-newfile").onclick = newFile;

  // global keys
  window.addEventListener("keydown", (e) => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); palOpen("cmd"); }
    else if (mod && e.key.toLowerCase() === "p") { e.preventDefault(); palOpen("file"); }
    else if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); saveActive(); }
    else if (mod && e.key === "`") { e.preventDefault(); $("dock").classList.toggle("collapsed"); }
    else if (mod && e.key === ",") { e.preventDefault(); switchPanel("settings"); }
    else if (mod && e.shiftKey && e.key.toLowerCase() === "f") { e.preventDefault(); switchPanel("search"); $("search-input").focus(); }
    else if (mod && e.shiftKey && e.key.toLowerCase() === "e") { e.preventDefault(); switchPanel("explorer"); }
    else if (e.key === "F5") { e.preventDefault(); playScene(); }
    else if (e.key === "Escape" && !$("overlay").classList.contains("hidden")) palClose();
  });

  // hide ctx menu on any click elsewhere
  window.addEventListener("mousedown", (e) => {
    if (!e.target.closest("#ctxmenu")) $("ctxmenu").classList.add("hidden");
  });

  // engine status
  if (window.dxn1?.onEngine) {
    window.dxn1.onEngine(({ up, info, demo }) => {
      $("engine-dot").classList.toggle("up", !!up);
      $("engine-label").textContent = up ? "engine" : (demo ? "demo" : "offline");
      $("st-engine").textContent = "ENGINE: " +
        (up ? `python · ${info?.workspace || "ok"}` : "demo mode");
    });
  }
}

/* ============================================================
   BOOT
   ============================================================ */
async function boot() {
  setTheme(STORE.get("theme", "dark"));
  setAccent(STORE.get("accent", "violet"));
  setFontSize(STORE.get("fs", 13.5));
  if (STORE.get("wrap", false)) {
    $("editor-stack").classList.add("wrap-on");
    $("set-wrap").checked = true;
  }
  FS = window.dxn1?.electron ? new ElectronFS() : new DemoFS();
  wire();
  renderRecents();
  try {
    const hello = await api("hello", {});
    $("st-engine").textContent = `ENGINE: ${hello.engine}`;
    $("engine-label").textContent = hello.engine === "demo" ? "demo" : "engine";
    $("engine-dot").classList.toggle("up", hello.engine !== "demo");
    if (hello.workspace && hello.workspace !== "demo") {
      $("project-name").textContent = hello.workspace.split(/[\\/]/).pop();
    }
    termPrint(`DXN1 STUDIO 3 — engine ${hello.engine} v${hello.version}`);
  } catch (e) {
    termPrint("engine offline — demo filesystem active");
  }
  await loadTree();
  await openSceneList();
  switchPanel(STORE.get("panel", "explorer"));
  say("STUDIO 3 ready — Ctrl K for commands, F5 to play");
}

boot();
