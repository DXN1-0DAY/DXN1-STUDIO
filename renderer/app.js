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
const VERSION = "3.0.03";

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
      this.put("scenes/level-2.dxn1.json",
        JSON.stringify(Spark.demoScene2(), null, 2));
      this.save();
      // a tiny honest git history for the demo filesystem
      this.vgit = { branch: "main", snap: { ...this.data }, commits: [
        { hash: "a1b3c9f", subject: "import playground + level-2",
          author: "you", when: "at import" } ] };
    }
  }
  put(path, content) { this.data[path] = content; this.save(); }
  save() { STORE.set("demo_fs", this.data); }
  _vgit() {
    if (!this.vgit) {
      this.vgit = STORE.get("demo_vgit", null);
    }
    if (!this.vgit || !this.vgit.branches) {
      // migrate/seed: one branch, per-branch snapshot + history
      const b = this.vgit && this.vgit.branch ? this.vgit.branch : "main";
      const snap = this.vgit && this.vgit.snap ? this.vgit.snap : { ...this.data };
      const commits = this.vgit && this.vgit.commits ? this.vgit.commits :
        [{ hash: "a1b3c9f", subject: "import playground + level-2",
           author: "you", when: "at import" }];
      this.vgit = { branch: b, branches: { [b]: { snap, commits } } };
      STORE.set("demo_vgit", this.vgit);
    }
    return this.vgit;
  }
  _vcur() { return this._vgit().branches[this._vgit().branch]; }
  /* LCS line diff — demo files are small, O(n·m) is fine here.
     Returns unified-style hunks with 2 lines of context. */
  static diffHunks(a, b) {
    const n = a.length, m = b.length;
    const ops = [];
    if (n * m > 400000) {              // too big — honest full-replace
      for (const s of a) ops.push({ t: "-", s });
      for (const s of b) ops.push({ t: "+", s });
    } else {
      const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
      for (let i = n - 1; i >= 0; i--)
        for (let j = m - 1; j >= 0; j--)
          dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1
                                   : Math.max(dp[i + 1][j], dp[i][j + 1]);
      let i = 0, j = 0;
      while (i < n && j < m) {
        if (a[i] === b[j]) { ops.push({ t: " ", s: a[i] }); i++; j++; }
        else if (dp[i + 1][j] >= dp[i][j + 1]) { ops.push({ t: "-", s: a[i] }); i++; }
        else { ops.push({ t: "+", s: b[j] }); j++; }
      }
      while (i < n) { ops.push({ t: "-", s: a[i++] }); }
      while (j < m) { ops.push({ t: "+", s: b[j++] }); }
    }
    // collapse into hunks with 2 context lines around each change run
    const hunks = [];
    const aNo = [], bNo = [];
    let ai = 1, bi = 1;
    for (const op of ops) {
      aNo.push(ai); bNo.push(bi);
      if (op.t === " ") { ai++; bi++; } else if (op.t === "-") { ai++; } else { bi++; }
    }
    const keep = ops.map((op, k) => op.t !== " " ||
      ops.slice(Math.max(0, k - 2), k + 3).some((o2) => o2.t !== " "));
    let buf = [];
    const flush = () => {
      if (!buf.length) return;
      const fA = aNo[buf[0].k], lA = aNo[buf[buf.length - 1].k];
      const fB = bNo[buf[0].k], lB = bNo[buf[buf.length - 1].k];
      hunks.push({
        header: `@@ -${fA},${lA - fA + 1} +${fB},${lB - fB + 1} @@`,
        lines: buf.map((x) => ({ t: x.op.t, s: x.op.s,
          n: x.op.t === "+" ? bNo[x.k] : aNo[x.k] })),
      });
      buf = [];
    };
    for (let k = 0; k < ops.length; k++) {
      if (keep[k]) buf.push({ op: ops[k], k });
      else if (buf.length && buf[buf.length - 1].op.t !== " ")
        buf.push({ op: { t: " ", s: "" }, k });   // visual break
      else if (buf.length) flush();
    }
    flush();
    return hunks;
  }
  _vdiff() {
    const g = this._vcur();
    const files = [];
    const seen = new Set();
    for (const [p, c] of Object.entries(this.data)) {
      seen.add(p);
      if (!(p in g.snap)) files.push({ path: p, x: "A", y: " " });
      else if (g.snap[p] !== c) files.push({ path: p, x: "M", y: " " });
    }
    for (const p of Object.keys(g.snap)) {
      if (!seen.has(p)) files.push({ path: p, x: "D", y: " " });
    }
    return files;
  }
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
      case "git_status": {
        const files = this._vdiff();
        return ok({ branch: this._vgit().branch, ahead: 0, files,
                    clean: files.length === 0 });
      }
      case "git_log":
        return ok({ commits: this._vcur().commits });
      case "git_commit": {
        const msg = String(args.message || "").trim();
        if (!msg) return bad("commit message required");
        const files = this._vdiff();
        if (!files.length) return bad("nothing to commit, working tree clean");
        const cur = this._vcur();
        const hash = Math.floor(Math.random() * 0xfffffff)
          .toString(16).padStart(7, "0").slice(0, 7);
        cur.commits.unshift({ hash, subject: msg, author: "you",
          when: "just now", files: files.length });
        cur.snap = { ...this.data };
        STORE.set("demo_vgit", this.vgit);
        return ok({ committed: hash, files: files.length });
      }
      case "git_branches": {
        const g3 = this._vgit();
        return ok({ branches: Object.keys(g3.branches),
                    current: g3.branch });
      }
      case "git_checkout": {
        const name = String(args.name || "").trim();
        if (!name || name.startsWith("-")) return bad("invalid branch name");
        const g4 = this._vgit();
        if (args.create) {
          if (g4.branches[name]) return bad(`branch already exists: ${name}`);
          g4.branches[name] = { snap: { ...this.data }, commits: [
            { hash: Math.floor(Math.random() * 0xfffffff).toString(16)
              .padStart(7, "0").slice(0, 7),
              subject: `branch created from ${g4.branch}`,
              author: "you", when: "just now", files: 0 } ] };
          g4.branch = name;
          STORE.set("demo_vgit", g4);
          return ok({ branch: name, created: true });
        }
        if (!g4.branches[name]) return bad(`no such branch: ${name}`);
        g4.branch = name;
        this.data = { ...g4.branches[name].snap };   // git checkout IS a restore
        this.save();
        STORE.set("demo_vgit", g4);
        return ok({ branch: name, created: false });
      }
      case "git_diff": {
        const p = String(args.path || "");
        const cur2 = this._vcur();
        const had = p in cur2.snap, has = p in this.data;
        if (!had && !has) return bad("no such file");
        if (had && this.data[p] === cur2.snap[p]) {
          return ok({ path: p, status: "clean", hunks: [] });
        }
        const a = had ? cur2.snap[p].split("\n") : [];
        const b = has ? this.data[p].split("\n") : [];
        return ok({ path: p, status: had ? "modified" : "added",
                    hunks: DemoFS.diffHunks(a, b) });
      }
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
    renderTabs(); renderHighlight(); renderGutter(); updatePos(); paintMinimap();
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
    el.draggable = true;
    el.innerHTML = `<span>${esc(t.path.split("/").pop())}</span>` +
      (t.dirty ? `<span class="dot">●</span>` : "") +
      `<span class="x" title="Close">✕</span>`;
    el.onclick = (e) => {
      if (e.target.classList.contains("x")) return closeTab(t.path);
      if (t.kind === "scene") openScene(t.path);
      else openPath(t.path);
    };
    // drag to reorder — the strip is yours
    el.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", t.path);
      e.dataTransfer.effectAllowed = "move";
      el.classList.add("dragging");
    });
    el.addEventListener("dragend", () => el.classList.remove("dragging"));
    el.addEventListener("dragover", (e) => {
      e.preventDefault(); el.classList.add("drop-target");
    });
    el.addEventListener("dragleave", () => el.classList.remove("drop-target"));
    el.addEventListener("drop", (e) => {
      e.preventDefault(); el.classList.remove("drop-target");
      const from = e.dataTransfer.getData("text/plain");
      if (!from || from === t.path) return;
      const fi = OPEN_TABS.findIndex((x) => x.path === from);
      const ti = OPEN_TABS.findIndex((x) => x.path === t.path);
      if (fi < 0 || ti < 0) return;
      const [moved] = OPEN_TABS.splice(fi, 1);
      OPEN_TABS.splice(ti, 0, moved);
      renderTabs();
    });
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
  if (["html", "htm", "svg", "xml"].includes(ext)) return "html";
  if (["css", "scss", "less"].includes(ext)) return "css";
  return "txt";
}

const PY_KW = "def|class|return|if|elif|else|for|while|import|from|as|with|try|except|finally|raise|lambda|pass|break|continue|and|or|not|in|is|None|True|False|global|nonlocal|yield|async|await|assert|del|match|case";
const JS_KW = "function|const|let|var|return|if|else|for|while|do|switch|case|break|continue|new|class|extends|super|this|typeof|instanceof|null|undefined|true|false|import|export|from|as|async|await|try|catch|finally|throw|yield|static|get|set|delete|void";

function highlight(src, lang) {
  const store = [];
  // Markers are LETTERS ONLY (bijective base-26): digit markers used to be
  // eaten by the later number rule, corrupting every stored token.
  const enc26 = (n) => {
    let s = "";
    n += 1;
    while (n > 0) {
      const r = (n - 1) % 26;
      s = String.fromCharCode(97 + r) + s;
      n = Math.floor((n - 1) / 26);
    }
    return s;
  };
  const dec26 = (s) => {
    let n = 0;
    for (const c of s) n = n * 26 + (c.charCodeAt(0) - 96);
    return n - 1;
  };
  const keep = (html) => {
    store.push(html);
    return `\u0000${enc26(store.length - 1)}\u0000`;
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
  if (lang === "css") {
    sub(/\/\*[\s\S]*?\*\//g, "com");
    sub(/@[\w-]+/g, "dec");
    sub(/#[0-9a-fA-F]{3,8}\b/g, "num");
    sub(/[.#][\w-]+/g, "fn");
    sub(/[\w-]+(?=\s*:)/g, "kw");
  }
  if (lang === "html") {
    sub(/&lt;!--[\s\S]*?--&gt;/g, "com");
    sub(/&lt;\/?[\w-]+/g, "kw");
    sub(/[\w-]+(?==)/g, "fn");
  }
  sub(/\b\d+(\.\d+)?\b/g, "num");
  sub(/@[\w.]+/g, "dec");
  sub(/\b([a-zA-Z_]\w*)\(/g, (m, f) =>
    keep(`<span class="tok-fn">${f}</span>(`));
  if (lang === "md") {
    sub(/^#{1,6} .*$/gm, "kw");
    sub(/\*\*[^*]+\*\*/g, "fn");
  }
  // unwrap — nested markers need passes until the string is stable
  let prev;
  do {
    prev = out;
    out = out.replace(/\u0000([a-z]+)\u0000/g, (_, w) => store[dec26(w)]);
  } while (out !== prev);
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
  updateCurline(line);
}

/* current-line highlight + gutter scroll sync */
function updateCurline(line) {
  const ta = $("editor");
  const cur = $("curline");
  if (!ACTIVE || $("editor-view").classList.contains("active") === false) {
    cur.classList.remove("on");
    return;
  }
  const lh = (parseFloat(getComputedStyle(ta).lineHeight) ||
              (STORE.get("fs", 13.5) * 1.6));
  const top = 12 + (line - 1) * lh - ta.scrollTop;
  const stackH = $("editor-stack").clientHeight || 0;
  if (top < -lh / 2 || top > stackH - 4) {
    cur.classList.remove("on");
  } else {
    cur.style.top = top + "px";
    cur.classList.add("on");
  }
}

function syncGutter() {
  const ta = $("editor");
  $("gutter").scrollTop = ta.scrollTop;
}

/* ============================================================
   FIND IN FILE — Ctrl+F, wrap-around, live count
   ============================================================ */
const FIND = { hits: [], idx: -1 };

function findOpen() {
  if (!ACTIVE) return toast("Nothing to find — open a file first", "err");
  $("findbar").classList.remove("hidden");
  const inp = $("find-inp");
  inp.focus();
  inp.select();
  findCompute();
}

function findClose() {
  $("findbar").classList.add("hidden");
  $("editor").focus();
}

function findCompute() {
  const q = $("find-inp").value;
  FIND.hits = [];
  FIND.idx = -1;
  if (!q) { $("find-count").textContent = "0/0"; return; }
  const src = $("editor").value.toLowerCase();
  const ql = q.toLowerCase();
  let at = src.indexOf(ql);
  while (at >= 0 && FIND.hits.length < 5000) {
    FIND.hits.push(at);
    at = src.indexOf(ql, at + ql.length);
  }
  findShow(1);                       // land on the first hit
}

function findShow(dir) {
  const n = FIND.hits.length;
  if (!n) { $("find-count").textContent = "0/0"; return; }
  FIND.idx = ((FIND.idx + dir) % n + n) % n;   // wraps both directions
  const ta = $("editor");
  const start = FIND.hits[FIND.idx];
  const q = $("find-inp").value;
  ta.focus();
  ta.setSelectionRange(start, start + q.length);
  const line = ta.value.slice(0, start).split("\n").length;
  const lh = parseFloat(getComputedStyle(ta).lineHeight) || 21;
  ta.scrollTop = Math.max(0, (line - 4) * lh);
  $("find-count").textContent = `${FIND.idx + 1}/${n}`;
}

/* ============================================================
   REPLACE IN FILE — extends the findbar (Ctrl+H focuses replace)
   ============================================================ */
function replaceOpen() {
  if (!ACTIVE) return toast("Nothing to replace — open a file first", "err");
  findOpen();
  $("replace-inp").focus();
}

function replaceOne() {
  const ta = $("editor");
  const q = $("find-inp").value;
  const rep = $("replace-inp").value;
  if (!q) return;
  const sel = ta.value.slice(ta.selectionStart, ta.selectionEnd);
  if (sel.toLowerCase() === q.toLowerCase()) {
    const start = ta.selectionStart;
    ta.setRangeText(rep, start, ta.selectionEnd, "end");
    editorChanged();
  }
  findCompute();
}

function replaceAll() {
  const q = $("find-inp").value;
  const rep = $("replace-inp").value;
  const ta = $("editor");
  if (!q) return;
  let n = 0;
  const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
  const out = ta.value.replace(re, () => { n++; return rep; });
  if (!n) { $("find-count").textContent = "0/0"; return say("nothing to replace"); }
  const pos = ta.selectionStart;
  ta.value = out;
  ta.setSelectionRange(Math.min(pos, out.length), Math.min(pos, out.length));
  editorChanged();
  FIND.hits = []; FIND.idx = -1;
  toast(`Replaced ${n} occurrence${n === 1 ? "" : "s"}`, "ok", 1800);
  findCompute();
}

/* ============================================================
   GO TO LINE — Ctrl+G
   ============================================================ */
function gotoOpen() {
  if (!ACTIVE) return toast("Open a file first", "err");
  $("gotobar").classList.remove("hidden");
  const inp = $("goto-inp");
  inp.value = "";
  inp.focus();
}

function gotoClose() {
  $("gotobar").classList.add("hidden");
  $("editor").focus();
}

function gotoLine(n) {
  const ta = $("editor");
  const lines = ta.value.split("\n");
  const line = Math.max(1, Math.min(lines.length, n || 1));
  let pos = 0;
  for (let i = 0; i < line - 1; i++) pos += lines[i].length + 1;
  ta.focus();
  ta.setSelectionRange(pos, pos + (lines[line - 1] || "").length);
  const lh = parseFloat(getComputedStyle(ta).lineHeight) || 21;
  ta.scrollTop = Math.max(0, (line - 4) * lh);
  gotoClose();
  updatePos();
  say("line " + line + " of " + lines.length);
}

/* ============================================================
   EDITOR EDIT PIPELINE — one function any edit goes through
   ============================================================ */
function editorChanged() {
  renderHighlight(); renderGutter(); updatePos(); paintMinimap();
  const tab = OPEN_TABS.find((t) => t.path === ACTIVE);
  if (tab && !tab.dirty) { tab.dirty = true; renderTabs(); }
}

// bracket/quote auto-close + selection wrap — small, honest, fast
const PAIRS = { "(": ")", "[": "]", "{": "}", '"': '"', "'": "'", "`": "`" };
const CLOSERS = new Set(Object.values(PAIRS));

function editorKeydown(e) {
  const ta = $("editor");
  if (e.key === "Tab") {                    // 2-space indent, always ours
    e.preventDefault();
    const s = ta.selectionStart, epos = ta.selectionEnd;
    ta.setRangeText("  ", s, epos, "end");
    editorChanged();
    return;
  }
  const open = PAIRS[e.key];
  const sel = ta.value.slice(ta.selectionStart, ta.selectionEnd);
  if (CLOSERS.has(e.key) && !sel &&
      ta.value[ta.selectionStart] === e.key) {     // type-over the closer first
    e.preventDefault();
    ta.setSelectionRange(ta.selectionStart + 1, ta.selectionStart + 1);
    return;
  }
  if (open && e.key !== "'") {              // quotes: only wrap selections
    e.preventDefault();
    const s0 = ta.selectionStart;
    if (sel) ta.setRangeText(e.key + sel + open,
      s0, ta.selectionEnd, "end");
    else {
      ta.setRangeText(e.key + open, s0, ta.selectionEnd, "end");
      ta.setSelectionRange(s0 + 1, s0 + 1);   // cursor between the pair
    }
    editorChanged();
    return;
  }
  if ((e.key === '"' || e.key === "'") && sel) {   // wrap selection in quotes
    e.preventDefault();
    ta.setRangeText(e.key + sel + e.key, ta.selectionStart, ta.selectionEnd, "end");
    editorChanged();
    return;
  }
  if (e.key === "Backspace" && !sel) {             // delete empty pairs
    const before = ta.value[ta.selectionStart - 1];
    const after = ta.value[ta.selectionStart];
    if (before && PAIRS[before] === after) {
      e.preventDefault();
      ta.setSelectionRange(ta.selectionStart - 1, ta.selectionStart + 1);
      ta.setRangeText("", ta.selectionStart, ta.selectionEnd, "end");
      editorChanged();
    }
  }
}

function editorCtxMenu(e) {
  const cmds = [
    { label: "Undo", run: () => document.execCommand("undo") },
    { label: "Redo", run: () => document.execCommand("redo") },
    "-",
    { label: "Cut", run: () => document.execCommand("cut") },
    { label: "Copy", run: () => document.execCommand("copy") },
    { label: "Paste", run: async () => {
        try { await navigator.clipboard.readText().then((t) => {
          const ta = $("editor");
          ta.setRangeText(t, ta.selectionStart, ta.selectionEnd, "end");
          editorChanged();
        }); } catch { toast("Clipboard blocked — press Ctrl+V", "info"); }
      } },
    { label: "Select all", run: () => $("editor").select() },
    "-",
    { label: "Find  (Ctrl+F)", run: () => findOpen() },
    { label: "Replace  (Ctrl+H)", run: () => replaceOpen() },
    { label: "Go to line  (Ctrl+G)", run: () => gotoOpen() },
  ];
  ctxMenu(e.clientX, e.clientY, cmds);
}

/* ============================================================
   MINIMAP — DS3 style: one bar per line + viewport lens
   ============================================================ */
let MM_PENDING = false;

function paintMinimap() {
  if (MM_PENDING) return;
  MM_PENDING = true;
  requestAnimationFrame(() => {
    MM_PENDING = false;
    const cv = $("minimap");
    const ta = $("editor");
    const stack = $("editor-stack");
    if (!stack.classList.contains("mm-on") ||
        !$("editor-view").classList.contains("active") || !ACTIVE) return;
    const dpr = window.devicePixelRatio || 1;
    const w = 86;
    const h = cv.clientHeight || stack.clientHeight || 300;
    if (cv.width !== Math.floor(w * dpr) || cv.height !== Math.floor(h * dpr)) {
      cv.width = Math.floor(w * dpr);
      cv.height = Math.floor(h * dpr);
    }
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const lines = ta.value.split("\n");
    const total = lines.length || 1;
    const lh = 3;                                   // px per line in the map
    const docH = total * lh;
    const scale = Math.min(1, h / docH);            // squeeze tall files
    const cs = getComputedStyle(document.documentElement);
    ctx.globalAlpha = 0.55;
    ctx.fillStyle = cs.getPropertyValue("--text3").trim() || "#5c6478";
    for (let i = 0; i < total; i++) {
      const y = i * lh * scale;
      if (y > h) break;
      const len = Math.min(lines[i].trim().length, 64);
      if (!len) continue;
      const indent = Math.min(lines[i].length - lines[i].trimStart().length, 24);
      ctx.fillRect(7 + indent * 0.7, y, Math.max(2, len * 0.9), 2);
    }
    // viewport lens
    const lensH = Math.max(24, ta.clientHeight * scale);
    const lensY = Math.min(h - lensH,
      (ta.scrollTop / (ta.scrollHeight || 1)) * (docH * scale));
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = cs.getPropertyValue("--accent").trim() || "#8b5cf6";
    ctx.fillRect(0, Math.max(0, lensY), w, lensH);
    ctx.globalAlpha = 1;
  });
}

function mmJump(e) {
  const ta = $("editor");
  const r = $("minimap").getBoundingClientRect();
  const ratio = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
  ta.scrollTop = ratio * (ta.scrollHeight - ta.clientHeight);
  paintMinimap();
}

function toggleMinimap() {
  const on = !$("editor-stack").classList.contains("mm-on");
  $("editor-stack").classList.toggle("mm-on", on);
  STORE.set("minimap", on);
  paintMinimap();
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
    onHit: () => say("ouch!"),
    onTransition: (nextPath) => transitionScene(nextPath),
    onStop: () => {
      $("btn-play").classList.remove("running");
      $("btn-play").textContent = "▶";
      GAME.repaint();            // back to the edit view instantly
    },
  });
  GAME.showGrid = GRID_ON;
  GAME.selected = SEL_ENT;
  GAME.repaint();                // the scene is visible the moment it opens
  wireSceneEditing();
  renderEntityList();
}

// goal reached — load scene.next and keep the run alive
async function transitionScene(nextPath) {
  if (!nextPath) { say("GOAL! — no next scene (set 'next' in the scene JSON)"); return; }
  try {
    const r = await api("scene_get", { path: nextPath });
    const name = nextPath.split("/").pop();
    toast("LEVEL CLEAR → " + name, "ok", 2000);
    SCENE_PATH = nextPath;
    OPEN_TABS = OPEN_TABS.filter((t) => t.path !== nextPath);
    OPEN_TABS.push({ path: nextPath, kind: "scene", dirty: false });
    ACTIVE = nextPath;
    $("scene-name").textContent = name;
    renderTabs();
    SEL_ENT = null;
    buildGame(r.scene);
    renderSceneDock(GAME.scene);
    GAME.start();                 // never make the player press play twice
    $("btn-play").classList.add("running");
    $("btn-play").textContent = "■";
  } catch (e) {
    toast("Next scene missing: " + nextPath, "err", 3200);
    say("transition failed: " + e.message);
  }
}

/* ============================================================
   ENTITY PALETTE — add · duplicate · delete · edit grid
   ============================================================ */
const ENT_PRESETS = {
  block:    () => ({ name: "block", w: 120, h: 36, color: "#1c2136", solid: true }),
  platform: () => ({ name: "platform", w: 170, h: 22, color: "#1c2136", solid: true }),
  coin:     () => ({ name: "coin", w: 22, h: 22, shape: "circle", color: "#fbbf24", tag: "coin" }),
  spike:    () => ({ name: "spike", w: 34, h: 28, shape: "triangle", color: "#fb7185", tag: "hazard" }),
  bouncer:  () => ({ name: "bouncer", w: 90, h: 22, color: "#22d3ee", solid: true, bounce: 1.4, tag: "bouncy" }),
  text:     () => ({ name: "label", w: 170, h: 30, text: "hello!", tsize: 22, color: "#9aa1b5" }),
  goal:     () => ({ name: "goal", w: 30, h: 64, color: "#34d399", tag: "goal" }),
  mover:    () => ({ name: "mover", w: 150, h: 22, color: "#22d3ee", solid: true,
                     path: { toX: 0, toY: 0, speed: 120 } }),
};

let GRID_ON = STORE.get("grid", true);

function setGrid(on) {
  GRID_ON = !!on;
  STORE.set("grid", GRID_ON);
  const b = $("btn-grid");
  if (b) b.classList.toggle("active", GRID_ON);
  if (GAME) { GAME.showGrid = GRID_ON; GAME.repaint(); }
}

function snap(v) {
  const g = ((GAME ? GAME.gridSize : 32) || 32) / 4;   // quarter-grid = 8px
  return Math.round(v / g) * g;
}

function uniqueName(base) {
  const names = new Set(GAME.scene.entities.map((e) => e.name));
  if (!names.has(base)) return base;
  for (let i = 2; ; i++) if (!names.has(`${base}-${i}`)) return `${base}-${i}`;
}

function addEntity(kind, at) {
  if (!GAME) return toast("Open a scene first", "err");
  const preset = ENT_PRESETS[kind];
  if (!preset) return;
  const e = Spark.makeEntity(preset());
  const cx = at ? at.x : GAME.scene.camera.x + GAME.canvas.width / (2 * (GAME.scene.camera.zoom || 1));
  const cy = at ? at.y : GAME.scene.camera.y + GAME.canvas.height / (2 * (GAME.scene.camera.zoom || 1));
  e.x = snap(cx - e.w / 2);
  e.y = snap(cy - e.h / 2);
  if (e.path) { e.path.toX = e.x + 160; e.path.toY = e.y; }  // movers get a rail
  e.name = uniqueName(e.name);
  GAME.scene.entities.push(e);
  SEL_ENT = e;
  GAME.selected = e;
  markSceneDirty();
  renderEntityList();
  renderInspector();
  GAME.repaint();
  say("added " + e.name);
}

// z-order — the entities array IS the paint order
function zOrder(dir) {
  if (!GAME || !SEL_ENT) return toast("No entity selected", "err");
  const list = GAME.scene.entities;
  const i = list.indexOf(SEL_ENT);
  if (i < 0) return;
  let j = i;
  if (dir === "front") j = list.length - 1;
  else if (dir === "back") j = 0;
  else if (dir === "up") j = Math.min(list.length - 1, i + 1);
  else if (dir === "down") j = Math.max(0, i - 1);
  if (j === i) return;
  list.splice(i, 1);
  list.splice(j, 0, SEL_ENT);
  markSceneDirty();
  renderEntityList();
  GAME.repaint();
  say(SEL_ENT.name + " → " + dir);
}

function dupEntity() {
  if (!GAME || !SEL_ENT) return toast("No entity selected", "err");
  const c = Spark.makeEntity(JSON.parse(JSON.stringify(SEL_ENT)));
  c.name = uniqueName(SEL_ENT.name);
  c.x += 24; c.y -= 24;
  GAME.scene.entities.push(c);
  SEL_ENT = c;
  GAME.selected = c;
  markSceneDirty();
  renderEntityList();
  renderInspector();
  GAME.repaint();
  toast("Duplicated → " + c.name, "ok", 1400);
}

function delEntity() {
  if (!GAME || !SEL_ENT) return toast("No entity selected", "err");
  const gone = SEL_ENT;
  GAME.scene.entities = GAME.scene.entities.filter((e) => e !== gone);
  SEL_ENT = null;
  GAME.selected = null;
  markSceneDirty();
  renderEntityList();
  renderInspector();
  GAME.repaint();
  toast("Deleted " + gone.name, "ok", 1400);
}

function gameView() { return $("game-view").classList.contains("active"); }

let SCENE_EDIT_WIRED = false;
function wireSceneEditing() {
  if (SCENE_EDIT_WIRED) return;
  SCENE_EDIT_WIRED = true;
  const cv = $("game-canvas");
  let dragging = null;
  let panning = null;
  let spaceHeld = false;

  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && gameView() && !(e.target.closest?.("input,textarea")))
      spaceHeld = true;
  });
  window.addEventListener("keyup", (e) => {
    if (e.code === "Space") spaceHeld = false;
  });

  // wheel zoom — toward the cursor, edit mode only
  cv.addEventListener("wheel", (e) => {
    if (!GAME || GAME.running) return;
    e.preventDefault();
    GAME.zoomAt(e.deltaY < 0 ? 1.1 : 1 / 1.1, e.clientX, e.clientY);
    GAME.repaint();
  }, { passive: false });

  cv.addEventListener("mousedown", (e) => {
    if (!GAME || GAME.running) return;   // editing is an EDITOR power
    if (e.button === 1 || (e.button === 0 && spaceHeld)) {
      e.preventDefault();
      panning = { sx: e.clientX, sy: e.clientY, cx: GAME.scene.camera.x,
                  cy: GAME.scene.camera.y };
      cv.style.cursor = "grabbing";
      return;
    }
    if (e.button !== 0) return;
    const w = GAME.screenToWorld(e.clientX, e.clientY);
    const ent = GAME.entityAt(w.x, w.y);
    SEL_ENT = ent;
    GAME.selected = ent;
    if (ent) {
      dragging = { ent, dx: w.x - ent.x, dy: w.y - ent.y };
      try { cv.setPointerCapture(e.pointerId); } catch {}   // synthetic events have no live pointer
    }
    renderEntityList(); renderInspector();
  });
  window.addEventListener("mousemove", (e) => {
    if (panning && GAME && !GAME.running) {
      const r = cv.getBoundingClientRect();
      const scale = cv.width / r.width / (GAME.scene.camera.zoom || 1);
      GAME.scene.camera.x = panning.cx - (e.clientX - panning.sx) * scale;
      GAME.scene.camera.y = panning.cy - (e.clientY - panning.sy) * scale;
      GAME.repaint();
      return;
    }
    if (!dragging || !GAME || GAME.running) return;
    const w = GAME.screenToWorld(e.clientX, e.clientY);
    dragging.ent.x = Math.round(w.x - dragging.dx);
    dragging.ent.y = Math.round(w.y - dragging.dy);
    if (GRID_ON && !e.altKey) {          // snap — Alt drags free
      dragging.ent.x = snap(dragging.ent.x);
      dragging.ent.y = snap(dragging.ent.y);
    }
    markSceneDirty();
    GAME.repaint();                       // live feedback while dragging
    renderInspector();                    // live numbers while dragging
  });
  window.addEventListener("mouseup", () => {
    dragging = null;
    if (panning) { panning = null; cv.style.cursor = ""; }
  });

  // canvas right-click — the scene toolbox comes to the cursor
  cv.addEventListener("contextmenu", (e) => {
    if (!GAME || GAME.running) return;
    e.preventDefault();
    const w = GAME.screenToWorld(e.clientX, e.clientY);
    const ent = GAME.entityAt(w.x, w.y);
    if (ent) { SEL_ENT = ent; GAME.selected = ent;
      renderEntityList(); renderInspector(); GAME.repaint(); }
    const items = [
      { label: "Add block here", run: () => addEntity("block", w) },
      { label: "Add platform here", run: () => addEntity("platform", w) },
      { label: "Add coin here", run: () => addEntity("coin", w) },
      { label: "Add spike here", run: () => addEntity("spike", w) },
      { label: "Add bouncer here", run: () => addEntity("bouncer", w) },
      { label: "Add mover here", run: () => addEntity("mover", w) },
      { label: "Add goal here", run: () => addEntity("goal", w) },
      "-",
      { label: "Duplicate" + (ent ? " — " + ent.name : ""), run: () => dupEntity(),
        disabled: !ent },
      { label: "Delete" + (ent ? " — " + ent.name : ""), run: () => delEntity(),
        danger: true, disabled: !ent },
      "-",
      { label: "Bring to front", run: () => zOrder("front"), disabled: !ent },
      { label: "Send to back", run: () => zOrder("back"), disabled: !ent },
    ];
    ctxMenu(e.clientX, e.clientY, items);
  });
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
      renderEntityList(); renderInspector(); GAME.repaint(); };
    el.oncontextmenu = (ev) => {          // right-click: quick actions
      ev.preventDefault();
      SEL_ENT = e; GAME.selected = e;
      renderEntityList(); renderInspector();
      ctxMenu(ev.clientX, ev.clientY, [
        { label: "Duplicate", run: () => dupEntity() },
        { label: "Delete", danger: true, run: () => delEntity() },
        "-",
        { label: "Bring to front", run: () => zOrder("front") },
        { label: "Send to back", run: () => zOrder("back") },
      ]);
    };
    host.appendChild(el);
  }
}

function renderInspector() {
  const host = $("inspector");
  host.innerHTML = "";
  if (!SEL_ENT) { host.innerHTML = `<div class="panel-note">click an entity on the canvas — drag to move · right-click list for actions</div>`; return; }
  const e = SEL_ENT;
  const row = (label, input) => {
    const r = document.createElement("div");
    r.className = "insp-row";
    r.innerHTML = `<label>${label}</label>`;
    r.appendChild(input);
    host.appendChild(r);
    return input;
  };
  const live = () => { markSceneDirty(); if (GAME && !GAME.running) GAME.repaint(); };
  const text = (val, on, type = "text") => {
    const i = document.createElement("input");
    i.type = type; i.value = val; i.spellcheck = false;
    i.oninput = () => { on(i.value); live(); };
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
  color.oninput = () => { e.color = color.value; renderEntityList(); live(); };
  row("color", color);
  const sel = document.createElement("select");
  for (const s of ["rect", "circle", "triangle"]) {
    const o = document.createElement("option");
    o.value = o.textContent = s; if (e.shape === s) o.selected = true;
    sel.appendChild(o);
  }
  sel.onchange = () => { e.shape = sel.value; live(); };
  row("shape", sel);
  row("text", text(e.text || "", (v) => { e.text = v; }));
  if (e.text) row("tsize", num(e.tsize || 22, (v) => e.tsize = v));
  const ctl = document.createElement("select");
  for (const s of ["none", "platformer"]) {
    const o = document.createElement("option");
    o.value = o.textContent = s; if (e.controls === s) o.selected = true;
    ctl.appendChild(o);
  }
  ctl.onchange = () => { e.controls = ctl.value; live(); };
  row("controls", ctl);
  const solid = document.createElement("input");
  solid.type = "checkbox"; solid.checked = !!e.solid; solid.className = "insp-check";
  solid.onchange = () => { e.solid = solid.checked; live(); };
  row("solid", solid);
  row("tag", text(e.tag || "", (v) => { e.tag = v; renderEntityList(); }));

  // motion — path entities shuttle between here and (toX, toY)
  if (e.path) {
    row("to x", num(e.path.toX, (v) => e.path.toX = v));
    row("to y", num(e.path.toY, (v) => e.path.toY = v));
    row("speed", num(e.path.speed, (v) => e.path.speed = v));
    const rm = document.createElement("button");
    rm.textContent = "⟲ Remove motion"; rm.className = "danger";
    rm.onclick = () => { e.path = null; markSceneDirty(); renderInspector(); live(); };
    const rr = document.createElement("div");
    rr.className = "insp-row"; rr.appendChild(rm);
    host.appendChild(rr);
  } else {
    const add = document.createElement("button");
    add.textContent = "⟶ Make it move";
    add.onclick = () => { e.path = { toX: e.x + 160, toY: e.y, speed: 120 };
      markSceneDirty(); renderInspector(); live(); };
    const ar = document.createElement("div");
    ar.className = "insp-row"; ar.appendChild(add);
    host.appendChild(ar);
  }

  const zos = document.createElement("div");
  zos.className = "insp-actions";
  const zl = (t, d, title) => {
    const b = document.createElement("button"); b.textContent = t;
    b.title = title; b.onclick = () => zOrder(d); return b;
  };
  zos.appendChild(zl("⤒ front", "front", "Bring to front"));
  zos.appendChild(zl("↑", "up", "One step forward"));
  zos.appendChild(zl("↓", "down", "One step backward"));
  zos.appendChild(zl("⤓ back", "back", "Send to back"));
  host.appendChild(zos);

  const acts = document.createElement("div");
  acts.className = "insp-actions";
  const bd = document.createElement("button");
  bd.textContent = "⧉ Duplicate";
  bd.onclick = () => dupEntity();
  const bx = document.createElement("button");
  bx.textContent = "✕ Delete"; bx.className = "danger";
  bx.onclick = () => delEntity();
  acts.appendChild(bd); acts.appendChild(bx);
  host.appendChild(acts);
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
   SOURCE CONTROL — honest wiring over the engine's git bridge
   ============================================================ */
async function renderGit() {
  const filesHost = $("git-files");
  const logHost = $("git-log");
  if (!filesHost) return;
  try {
    const st = await api("git_status", {});
    $("git-branch").textContent = `⑂ ${st.branch}` +
      (st.ahead ? ` ↑${st.ahead}` : "") +
      (st.clean ? " — clean" : ` — ${st.files.length} change${st.files.length === 1 ? "" : "s"}`);
    $("git-branch").style.cursor = "pointer";
    $("git-branch").title = "Click to switch or create a branch";
    $("st-branch").textContent = `⑂ ${st.branch}`;
    filesHost.innerHTML = "";
    if (!st.files.length) {
      filesHost.innerHTML = `<div class="panel-note">working tree clean</div>`;
    }
    for (const f of st.files) {
      const el = document.createElement("div");
      el.className = "git-file";
      const badge = { A: "gs-a", M: "gs-m", D: "gs-d", U: "gs-u", "?": "gs-u" }[f.x] || "gs-m";
      el.innerHTML = `<span class="gs-badge ${badge}">${esc(f.x)}</span>` +
        `<span class="gf-path" title="${esc(f.path)}">${esc(f.path)}</span>` +
        `<button class="mini gf-diff" title="View diff vs HEAD">±</button>`;
      el.onclick = () => f.x !== "D" && openPath(f.path);
      el.querySelector(".gf-diff").onclick = (ev) => {
        ev.stopPropagation();
        openDiff(f.path);
      };
      filesHost.appendChild(el);
    }
    const cntEl = $("rail-git-count");
    if (cntEl) {
      const cnt = st.files.length;
      cntEl.textContent = cnt > 9 ? "9+" : String(cnt);
      cntEl.classList.toggle("hidden", !cnt);
    }
    const lg = await api("git_log", {});
    logHost.innerHTML = "";
    for (const c of (lg.commits || []).slice(0, 12)) {
      const el = document.createElement("div");
      el.className = "git-commit";
      el.innerHTML = `<span class="gc-hash">${esc(c.hash)}</span>` +
        `<span class="gc-sub" title="${esc(c.subject)}">${esc(c.subject)}</span>` +
        `<span class="gc-when">${esc(c.when || "")}</span>`;
      logHost.appendChild(el);
    }
  } catch (e) {
    $("git-branch").textContent = "⑂ no git";
    $("st-branch").textContent = "⑂ —";
    filesHost.innerHTML = `<div class="panel-note">git: ${esc(e.message)}</div>`;
    if (logHost) logHost.innerHTML = "";
    const cntEl = $("rail-git-count");
    if (cntEl) cntEl.classList.add("hidden");
  }
}

async function gitCommit() {
  const msg = $("git-msg").value.trim();
  if (!msg) return toast("Write a commit message first", "err");
  try {
    const r = await api("git_commit", { message: msg });
    $("git-msg").value = "";
    toast(`Committed ${r.committed} (${r.files} file${r.files === 1 ? "" : "s"})`, "ok");
    renderGit();
    say("committed " + r.committed);
  } catch (e) { toast("Commit failed: " + e.message, "err"); }
}

async function gitBranchMenu(x, y) {
  try {
    const r = await api("git_branches", {});
    const items = r.branches.map((b) => ({
      label: (b === r.current ? "● " : "  ") + b,
      run: async () => {
        if (b === r.current) return;
        try {
          await api("git_checkout", { name: b });
          toast("Switched to " + b, "ok", 1800);
          await loadTree();
          renderGit();
        } catch (e) { toast("Checkout failed: " + e.message, "err"); }
      },
    }));
    items.push("-", {
      label: "＋ Create branch…",
      run: async () => {
        const name = prompt("New branch name:", "feature/");
        if (!name) return;
        try {
          await api("git_checkout", { name, create: true });
          toast("On new branch " + name, "ok", 1800);
          renderGit();
        } catch (e) { toast("Branch failed: " + e.message, "err"); }
      },
    });
    ctxMenu(x, y, items);
  } catch (e) { toast("Branches: " + e.message, "err"); }
}

/* ============================================================
   DIFF VIEWER — what changed vs HEAD, one file at a time
   ============================================================ */
async function openDiff(path) {
  try {
    const r = await api("git_diff", { path });
    const host = $("diff-body");
    host.innerHTML = "";
    $("diff-path").textContent = path;
    let adds = 0, dels = 0;
    for (const h of (r.hunks || [])) {
      const hEl = document.createElement("div");
      hEl.className = "dh-header";
      hEl.textContent = h.header;
      host.appendChild(hEl);
      for (const ln of h.lines) {
        const el = document.createElement("div");
        el.className = "dl" +
          (ln.t === "+" ? " dl-add" : ln.t === "-" ? " dl-del" : "");
        const sign = ln.t === "+" ? "+" : ln.t === "-" ? "\u2212" : " ";
        const no = ln.n ? String(ln.n).padStart(3, " ") : "   ";
        el.innerHTML = `<span class="dl-no">${no}</span>` +
          `<span class="dl-sign">${sign}</span>` +
          `<span class="dl-src">${esc(ln.s) || " "}</span>`;
        if (ln.t === "+") adds++;
        if (ln.t === "-") dels++;
        host.appendChild(el);
      }
    }
    $("diff-stat").textContent = r.status === "clean"
      ? "no changes" : `+${adds} \u2212${dels}`;
    if (!(r.hunks || []).length) {
      host.innerHTML = `<div class="panel-note" style="padding:18px">` +
        `No differences vs HEAD.</div>`;
    }
    $("diffview").classList.remove("hidden");
  } catch (e) { toast("Diff failed: " + e.message, "err"); }
}

function closeDiff() { $("diffview").classList.add("hidden"); }

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
  { ico: "⌕", label: "Find in file", key: "Ctrl+F", run: () => findOpen() },
  { ico: "⇄", label: "Replace in file", key: "Ctrl+H", run: () => replaceOpen() },
  { ico: "→", label: "Go to line", key: "Ctrl+G", run: () => gotoOpen() },
  { ico: "▦", label: "Toggle minimap", run: () => toggleMinimap() },
  { ico: "⌗", label: "Toggle edit grid", run: () => setGrid(!GRID_ON) },
  { ico: "⊕", label: "Zoom fit (scene)", run: () => GAME && GAME.zoomFit() },
  { ico: "⑂", label: "Refresh source control", run: () => { switchPanel("git"); renderGit(); } },
  { ico: "⧉", label: "Duplicate entity", key: "Ctrl+D", run: () => dupEntity() },
  { ico: "✕", label: "Delete entity", key: "Del", run: () => delEntity() },
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
    "       play [scene] · theme · accent <name> · grid · ent · find <text>\n" +
    "       git · zoom in|out|fit · mm · about · date · echo <text>"),
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
  grid: () => { setGrid(!GRID_ON); termPrint("edit grid: " + (GRID_ON ? "on" : "off")); },
  ent: () => termPrint(GAME ? GAME.scene.entities.map((e) =>
    `${e.name} @ ${Math.round(e.x)},${Math.round(e.y)}${e.tag ? " · " + e.tag : ""}`).join("\n")
    : "(no scene open)"),
  find: (a) => { if (!a.length) return termPrint("usage: find <text>");
    findOpen(); $("find-inp").value = a.join(" "); findCompute(); },
  git: async () => {
    try {
      const st = await api("git_status", {});
      termPrint(`⑂ ${st.branch}${st.ahead ? " ↑" + st.ahead : ""} — ` +
        (st.clean ? "clean" : st.files.map((f) => f.x + " " + f.path).join("\n       ")));
      const lg = await api("git_log", {});
      for (const c of (lg.commits || []).slice(0, 5)) {
        termPrint(`${c.hash} ${c.subject} (${c.when})`);
      }
    } catch (e) { termPrint("git: " + e.message); }
  },
  zoom: (a) => {
    if (!GAME) return termPrint("(no scene open)");
    const cam = GAME.scene.camera;
    if (a[0] === "fit") GAME.zoomFit();
    else if (a[0] === "in") { cam.zoom = Math.min(4, (cam.zoom || 1) * 1.25); GAME.repaint(); }
    else if (a[0] === "out") { cam.zoom = Math.max(0.3, (cam.zoom || 1) / 1.25); GAME.repaint(); }
    else termPrint("usage: zoom in|out|fit — current " + (cam.zoom || 1).toFixed(2));
  },
  mm: () => toggleMinimap(),
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
   SETTINGS (theme / accent / editor / keybindings)
   ============================================================ */
const KEYBINDS = [
  ["Ctrl K", "Command palette"], ["Ctrl P", "Quick open file"],
  ["Ctrl S", "Save"], ["Ctrl F", "Find in file"],
  ["Ctrl H", "Replace in file"], ["Ctrl G", "Go to line"],
  ["Ctrl `", "Terminal"], ["Ctrl ,", "Settings"],
  ["Ctrl ⇧ F", "Search in project"], ["Ctrl ⇧ E", "Explorer"],
  ["Ctrl D", "Duplicate entity"], ["Del", "Delete entity"],
  ["Wheel", "Zoom scene (edit)"], ["Space+drag", "Pan scene (edit)"],
  ["F5", "Play / stop scene"], ["Esc", "Close overlays"],
];

function renderKeybinds() {
  const host = $("kb-table");
  if (!host) return;
  host.innerHTML = "";
  for (const [k, d] of KEYBINDS) {
    const r = document.createElement("div");
    r.className = "kb-row";
    r.innerHTML = `<span>${d}</span><kbd>${k}</kbd>`;
    host.appendChild(r);
  }
}

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
  paintMinimap();
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
  if (name === "git") renderGit();
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
    if (it.disabled) { b.disabled = true; b.style.opacity = ".4"; }
    else b.onclick = () => { m.classList.add("hidden"); it.run(); };
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
  ed.addEventListener("input", editorChanged);
  ed.addEventListener("keydown", editorKeydown);
  ed.addEventListener("contextmenu", (e) => { e.preventDefault(); editorCtxMenu(e); });
  ed.addEventListener("keyup", updatePos);
  ed.addEventListener("click", updatePos);
  ed.addEventListener("scroll", () => { syncGutter(); updateCurline(
    (ed.value.slice(0, ed.selectionStart).split("\n")).length); });
  window.addEventListener("resize", () => { syncGutter(); });

  // scene dock
  $("scene-save").onclick = saveScene;

  // entity palette + scene editing buttons
  document.querySelectorAll(".ep").forEach((b) =>
    b.onclick = () => addEntity(b.dataset.ent));
  $("btn-grid").onclick = () => setGrid(!GRID_ON);
  $("btn-fit").onclick = () => { if (GAME) { GAME.zoomFit(); say("zoom fit"); } };
  $("btn-dup").onclick = () => dupEntity();
  $("btn-del-ent").onclick = () => delEntity();

  // find + replace in file
  $("find-inp").addEventListener("input", () => { FIND.idx = -1; findCompute(); });
  $("find-inp").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); findShow(e.shiftKey ? -1 : 1); }
    else if (e.key === "Escape") findClose();
  });
  $("find-next").onclick = () => findShow(1);
  $("find-prev").onclick = () => findShow(-1);
  $("find-close").onclick = findClose;
  $("replace-inp").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); replaceOne(); }
    else if (e.key === "Escape") findClose();
  });
  $("btn-replace").onclick = replaceOne;
  $("btn-replace-all").onclick = replaceAll;

  // go to line
  $("goto-inp").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); gotoLine(Number($("goto-inp").value)); }
    else if (e.key === "Escape") gotoClose();
  });
  $("goto-close").onclick = gotoClose;

  // minimap: click + drag to jump
  const mm = $("minimap");
  let mmDrag = false;
  mm.addEventListener("mousedown", (e) => { mmDrag = true; mmJump(e); });
  window.addEventListener("mousemove", (e) => { if (mmDrag) mmJump(e); });
  window.addEventListener("mouseup", () => { mmDrag = false; });

  // sidebar resize
  const sh = $("side-handle");
  sh.addEventListener("mousedown", (e) => {
    e.preventDefault();
    sh.classList.add("dragging");
    const move = (ev) => {
      const w = Math.min(480, Math.max(180, ev.clientX));
      document.documentElement.style.setProperty("--side-w", w + "px");
      STORE.set("side-w", w);
    };
    const up = () => {
      sh.classList.remove("dragging");
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  });

  // search
  let searchT = 0;
  $("search-input").addEventListener("input", (e) => {
    clearTimeout(searchT);
    searchT = setTimeout(() => runSearch(e.target.value), 240);
  });

  // source control
  $("git-commit").onclick = gitCommit;
  $("git-msg").addEventListener("keydown", (e) => {
    if (e.key === "Enter") gitCommit();
  });
  $("git-refresh").onclick = renderGit;
  $("git-branch").onclick = (e) => gitBranchMenu(e.clientX, e.clientY);

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
    const inField = e.target.closest?.("input,textarea,select");
    if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); palOpen("cmd"); }
    else if (mod && e.key.toLowerCase() === "p") { e.preventDefault(); palOpen("file"); }
    else if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); saveActive(); }
    else if (mod && e.key.toLowerCase() === "f" && !e.shiftKey) { e.preventDefault(); findOpen(); }
    else if (mod && e.key.toLowerCase() === "h") { e.preventDefault(); replaceOpen(); }
    else if (mod && e.key.toLowerCase() === "g") { e.preventDefault(); gotoOpen(); }
    else if (mod && e.key === "`") { e.preventDefault(); $("dock").classList.toggle("collapsed"); }
    else if (mod && e.key === ",") { e.preventDefault(); switchPanel("settings"); }
    else if (mod && e.shiftKey && e.key.toLowerCase() === "f") { e.preventDefault(); switchPanel("search"); $("search-input").focus(); }
    else if (mod && e.shiftKey && e.key.toLowerCase() === "e") { e.preventDefault(); switchPanel("explorer"); }
    else if (e.key === "Delete" && !inField && gameView()) { delEntity(); }
    else if (mod && e.key.toLowerCase() === "d" && !inField && gameView()) { e.preventDefault(); dupEntity(); }
    else if (e.key === "F5") { e.preventDefault(); playScene(); }
    else if (e.key === "Escape") {
      if (!$("diffview").classList.contains("hidden")) closeDiff();
      else if (!$("findbar").classList.contains("hidden")) findClose();
      else if (!$("gotobar").classList.contains("hidden")) gotoClose();
      else if (!$("overlay").classList.contains("hidden")) palClose();
    }
  });

  // hide ctx menu on any click elsewhere
  window.addEventListener("mousedown", (e) => {
    if (!e.target.closest("#ctxmenu")) $("ctxmenu").classList.add("hidden");
  });

  // diff viewer
  $("diff-close").onclick = closeDiff;
  $("diffview").addEventListener("mousedown", (e) => {
    if (e.target.id === "diffview") closeDiff();
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
  if (!STORE.get("minimap", true)) $("editor-stack").classList.remove("mm-on");
  const sw = STORE.get("side-w", 0);
  if (sw) document.documentElement.style.setProperty("--side-w", sw + "px");
  renderKeybinds();
  window.addEventListener("resize", paintMinimap);
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
  renderGit();                 // source control wakes up with everything else
  switchPanel(STORE.get("panel", "explorer"));
  setGrid(GRID_ON);          // paint the grid button state
  say("STUDIO 3 ready — Ctrl K for commands, F5 to play");
}

boot();
