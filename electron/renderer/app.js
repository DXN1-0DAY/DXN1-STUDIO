// DXN1 STUDIO — Electron renderer.
// Every control works. When the Python engine is unreachable the UI
// degrades into a real demo workspace (virtual FS) instead of dying.
'use strict';

/* ════════════════════════════ helpers ════════════════════════════ */
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
            "'": '&#39;' }[c]));
const basename = (p) => p.split('/').pop();
const dirname = (p) => (p.includes('/') ? p.slice(0, p.lastIndexOf('/')) : '');
const fmtSize = (n) => n < 1024 ? n + ' B'
  : n < 1048576 ? (n / 1024).toFixed(1) + ' KB'
  : (n / 1048576).toFixed(1) + ' MB';

const LANGS = {
  py: 'python', js: 'javascript', mjs: 'javascript', cjs: 'javascript',
  ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
  json: 'json', html: 'html', htm: 'html', css: 'css', md: 'markdown',
  sh: 'shell', bash: 'shell', yml: 'yaml', yaml: 'yaml', txt: 'plain text',
};
const langOf = (p) => LANGS[p.split('.').pop().toLowerCase()] || 'plain text';

/* ═════════════════════════════ state ═════════════════════════════ */
const S = {
  bridge: false,        // engine reachable
  demo: false,          // degraded demo mode
  ws: '', wsName: '',
  tree: [],             // flat [{path,size,mtime}]
  tabs: [],             // [{path, content, lang}]
  active: null,
  dirty: new Set(),
  settings: {
    mode: 'dark', accent: 'violet', font: 14,
    autosave: false, wrap: false,
  },
  openDirs: new Set(),
  selected: null,
  findHits: [], findIdx: -1,
  termHistory: [], termHidx: -1,
};

const LS = {
  get(k, d) { try { const v = localStorage.getItem(k);
    return v == null ? d : JSON.parse(v); } catch (_) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); }
    catch (_) {} },
};

/* ════════════════════════ engine client ══════════════════════════ */
const DEMO_SEED = {
  'README.md': '# Demo workspace\n\nThe engine is offline, so this is a \
local demo workspace stored in your browser.\nEverything works: create, \
edit, save, rename, delete.\n',
  'main.py': 'def greet(name):\n    print(f"hello {name}")\n\n\nif \
__name__ == "__main__":\n    greet("studio")\n',
  'app.js': 'function boot() {\n  console.log("dxn1 demo");\n}\n\nboot();\n',
};

function demoFs() {
  let fs = LS.get('dxn1-demo-fs', null);
  if (!fs) { fs = Object.assign({}, DEMO_SEED); LS.set('dxn1-demo-fs', fs); }
  return fs;
}
function demoTree() {
  const fs = demoFs();
  return Object.keys(fs).map((p) => ({ path: p, size: fs[p].length,
                                       mtime: 0 }));
}
const DEMO = {
  hello: () => ({ app: 'DXN1 STUDIO', version: 'demo', channel: 'demo',
                  workspace: '(demo workspace)', python: '—' }),
  tree: () => ({ entries: demoTree(), truncated: false }),
  read_file: ({ path }) => {
    const fs = demoFs();
    if (!(path in fs)) throw new Error('file not found: ' + path);
    return { path, content: fs[path], size: fs[path].length, mtime: 0 };
  },
  write_file: ({ path, content }) => {
    const fs = demoFs(); fs[path] = content || '';
    LS.set('dxn1-demo-fs', fs);
    return { path, size: (content || '').length };
  },
  rename_path: ({ from, to }) => {
    const fs = demoFs();
    if (!(from in fs)) throw new Error('not found: ' + from);
    if (to in fs) throw new Error('destination exists: ' + to);
    fs[to] = fs[from]; delete fs[from]; LS.set('dxn1-demo-fs', fs);
    return {};
  },
  delete_path: ({ path }) => {
    const fs = demoFs(); delete fs[path]; LS.set('dxn1-demo-fs', fs);
    return {};
  },
  make_dir: () => ({}),
  stat: ({ path }) => ({ path, exists: path in demoFs(), is_dir: false,
                         size: 0, mtime: 0 }),
  workspace_set: () => { throw new Error('not available in demo mode'); },
  reveal: () => { throw new Error('not available in demo mode'); },
  open_external: () => { throw new Error('not available in demo mode'); },
};

async function api(cmd, args) {
  if (S.demo) {
    const fn = DEMO[cmd];
    if (!fn) throw new Error('unknown command: ' + cmd);
    return fn(args || {});
  }
  const r = await window.dxn1.request(cmd, args || {});
  if (!r.ok) throw new Error(r.error || 'engine error');
  return r.result;
}

/* ═══════════════════════════ toasts ══════════════════════════════ */
function toast(msg, kind = 'info', ms = 2600) {
  const el = document.createElement('div');
  el.className = 'toast ' + (kind === 'ok' || kind === 'err' ||
                             kind === 'warn' ? kind : '');
  el.innerHTML = '<span class="tx">' + esc(msg) + '</span>' +
    '<button class="tb" aria-label="Dismiss">✕</button>';
  const kill = () => { el.classList.add('bye');
    setTimeout(() => el.remove(), 200); };
  el.querySelector('.tb').onclick = kill;
  $('toasts').appendChild(el);
  if (ms) setTimeout(kill, ms);
}

/* ═══════════════════════════ modal ═══════════════════════════════ */
let modalCb = null;
function confirmBox(title, text, cb, okLabel = 'Confirm') {
  $('modalTitle').textContent = title;
  $('modalText').textContent = text;
  $('modalOk').textContent = okLabel;
  modalCb = cb;
  openLayer('modal');
  $('modalOk').focus();
}
function promptBox(title, placeholder, value, cb) {
  const wrap = document.createElement('div');
  wrap.className = 'dialog';
  wrap.id = 'promptDialog';
  wrap.innerHTML =
    '<div class="dialog-head">' + esc(title) + '</div>' +
    '<input class="field" id="promptInput" placeholder="' +
    esc(placeholder || '') + '" style="margin:14px 16px 6px;' +
    'width:calc(100% - 32px)" />' +
    '<div class="modal-actions">' +
    '<button class="btn ghost" id="promptCancel">Cancel</button>' +
    '<button class="btn" id="promptOk">Create</button></div>';
  $('overlay').classList.remove('hidden');
  document.body.appendChild(wrap);
  const inp = wrap.querySelector('#promptInput');
  inp.value = value || '';
  const done = (val) => {
    wrap.remove();
    if (!document.querySelector('.dialog:not(.hidden), .panel:not(.hidden)'))
      $('overlay').classList.add('hidden');
    if (val != null && val.trim()) cb(val.trim());
  };
  wrap.querySelector('#promptOk').onclick = () => done(inp.value);
  wrap.querySelector('#promptCancel').onclick = () => done(null);
  inp.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') done(inp.value);
    if (e.key === 'Escape') done(null);
    e.stopPropagation();
  });
  setTimeout(() => { inp.focus(); inp.select(); }, 30);
}

/* ═════════════════════════ layers ════════════════════════════════ */
const LAYERS = ['palette', 'quickopen', 'overview', 'settings', 'modal'];
function openLayer(name) {
  $('overlay').classList.remove('hidden');
  $(name).classList.remove('hidden');
  const f = $(name).querySelector('input');
  if (f) setTimeout(() => f.focus(), 20);
}
function closeLayer(name) {
  $(name).classList.add('hidden');
  if (!LAYERS.some((l) => !$(l).classList.contains('hidden')))
    $('overlay').classList.add('hidden');
}
function closeTopLayer() {
  for (const id of ['promptDialog', 'modal', 'palette', 'quickopen',
                    'overview', 'settings']) {
    const el = $(id);
    if (el && !el.classList.contains('hidden')) {
      if (id === 'promptDialog') { el.remove();
        $('overlay').classList.add('hidden'); return true; }
      closeLayer(id);
      return true;
    }
  }
  return false;
}
function anyLayerOpen() {
  return LAYERS.some((l) => !$(l).classList.contains('hidden')) ||
    !!document.getElementById('promptDialog');
}

/* ════════════════════════════ tree ═══════════════════════════════ */
function buildHierarchy(entries) {
  const root = { dirs: {}, files: [] };
  for (const e of entries) {
    const parts = e.path.split('/');
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const d = parts[i];
      if (!node.dirs[d]) node.dirs[d] = { dirs: {}, files: [] };
      node = node.dirs[d];
    }
    node.files.push({ name: parts[parts.length - 1], path: e.path,
                      size: e.size });
  }
  const sortNode = (n) => {
    n.files.sort((a, b) => a.name.localeCompare(b.name));
    Object.keys(n.dirs).sort().forEach((k) => sortNode(n.dirs[k]));
  };
  sortNode(root);
  return root;
}

function renderTree() {
  const host = $('fileTree');
  host.innerHTML = '';
  const hier = buildHierarchy(S.tree);
  const frag = document.createDocumentFragment();

  const walk = (node, prefix, depth) => {
    for (const dname of Object.keys(node.dirs)) {
      const full = prefix ? prefix + '/' + dname : dname;
      const open = S.openDirs.has(full);
      const row = document.createElement('div');
      row.className = 'tree-row dir' + (open ? ' open' : '');
      row.setAttribute('role', 'treeitem');
      row.setAttribute('aria-expanded', String(open));
      row.innerHTML = '<span class="tree-indent" style="width:' +
        (depth * 12) + 'px"></span><span class="tw">▶</span>' +
        '<span class="fi">📁</span><span class="nm">' +
        esc(dname) + '</span>';
      row.onclick = () => {
        (open ? S.openDirs.delete(full) : S.openDirs.add(full));
        renderTree();
      };
      row.oncontextmenu = (e) => treeCtx(e, full, true);
      frag.appendChild(row);
      if (open) walk(node.dirs[dname], full, depth + 1);
    }
    for (const f of node.files) {
      const row = document.createElement('div');
      row.className = 'tree-row' +
        (S.selected === f.path ? ' selected' : '');
      row.setAttribute('role', 'treeitem');
      row.dataset.path = f.path;
      row.innerHTML = '<span class="tree-indent" style="width:' +
        (depth * 12) + 'px"></span><span class="tw"></span>' +
        '<span class="fi">' + fileIcon(f.name) + '</span>' +
        '<span class="nm">' + esc(f.name) + '</span>' +
        '<span class="meta">' + fmtSize(f.size) + '</span>';
      row.onclick = () => openFile(f.path);
      row.oncontextmenu = (e) => treeCtx(e, f.path, false);
      frag.appendChild(row);
    }
  };
  walk(hier, '', 0);
  host.appendChild(frag);
  $('treeEmpty').classList.toggle('hidden', S.tree.length > 0);
}

function fileIcon(name) {
  const e = name.split('.').pop().toLowerCase();
  return { py: '🐍', js: '📜', mjs: '📜', cjs: '📜', ts: '📜',
           json: '🧩', html: '🌐', css: '🎨', md: '📖', sh: '⌨️',
           yml: '⚙️', yaml: '⚙️', txt: '📄' }[e] || '📄';
}

async function refreshTree(quiet) {
  try {
    const r = await api('tree', {});
    S.tree = r.entries || [];
    renderTree();
    if (!quiet) $('tbTitle').textContent =
      S.wsName + ' — ' + S.tree.length + ' files';
  } catch (err) {
    if (!quiet) toast('Could not list files: ' + err.message, 'err');
  }
}

function treeCtx(e, path, isDir) {
  e.preventDefault();
  e.stopPropagation();
  selectRow(path);
  ctxMenu(e.clientX, e.clientY, [
    ...(isDir ? [] : [
      { label: 'Open', fn: () => openFile(path) },
    ]),
    { label: 'New file here', fn: () =>
      promptBox('New file', 'name.py', '', (name) =>
        createFile(path ? dirname(path) + '/' + name : name)) },
    { label: 'New folder here', fn: () =>
      promptBox('New folder', 'folder', '', async (name) => {
        const base = path ? dirname(path) : '';
        const full = (base ? base + '/' : '') + name;
        try { await api('make_dir', { path: full });
          await refreshTree(true); toast('Folder created', 'ok'); }
        catch (err) { toast(err.message, 'err'); }
      }) },
    { sep: true },
    ...(isDir ? [] : [
      { label: 'Rename…', fn: () =>
        promptBox('Rename', 'new name', basename(path), async (name) => {
          const to = dirname(path) ? dirname(path) + '/' + name : name;
          try { await api('rename_path', { from: path, to });
            renameEverywhere(path, to); await refreshTree(true);
            toast('Renamed', 'ok'); }
          catch (err) { toast(err.message, 'err'); }
        }) },
      { label: 'Delete', danger: true, fn: () =>
        confirmBox('Delete file',
          'Delete ' + basename(path) + '? This cannot be undone.',
          async () => {
            try { await api('delete_path', { path });
              if (S.tabs.some((t) => t.path === path)) closeTab(path);
              await refreshTree(true); toast('Deleted', 'ok'); }
            catch (err) { toast(err.message, 'err'); }
          }, 'Delete') },
    ]),
    { label: 'Copy path', fn: () =>
      window.dxn1.clipboardWrite(path).then(() =>
        toast('Path copied', 'ok', 1400)) },
    { label: 'Reveal in file manager', fn: () =>
      api('reveal', { path }).catch((err) => toast(err.message, 'err')) },
  ]);
}

function selectRow(path) {
  S.selected = path;
  document.querySelectorAll('.tree-row').forEach((r) =>
    r.classList.toggle('selected', r.dataset.path === path));
}

async function createFile(path) {
  try {
    await api('write_file', { path, content: '' });
    S.openDirs.add(dirname(path));
    await refreshTree(true);
    openFile(path);
    toast('Created ' + basename(path), 'ok', 1600);
  } catch (err) { toast(err.message, 'err'); }
}

function renameEverywhere(from, to) {
  for (const t of S.tabs) if (t.path === from) t.path = to;
  if (S.active === from) S.active = to;
  const d = S.dirty;
  if (d.has(from)) { d.delete(from); d.add(to); }
  renderTabs();
}

/* ════════════════════════════ tabs ═══════════════════════════════ */
function renderTabs() {
  const host = $('tabs');
  host.innerHTML = '';
  for (const t of S.tabs) {
    const el = document.createElement('div');
    el.className = 'tab' + (t.path === S.active ? ' active' : '');
    el.setAttribute('role', 'tab');
    el.setAttribute('aria-selected',
                    String(t.path === S.active));
    el.title = t.path;
    el.innerHTML = '<span class="t-dirty"' +
      (S.dirty.has(t.path) ? '' : ' style="visibility:hidden"') +
      '>●</span><span class="t-name">' + esc(basename(t.path)) +
      '</span><button class="t-close" aria-label="Close tab">✕</button>';
    el.onclick = (e) => {
      if (e.target.classList.contains('t-close')) return;
      activateTab(t.path);
    };
    el.onauxclick = (e) => { if (e.button === 1) closeTab(t.path); };
    el.querySelector('.t-close').onclick = () => closeTab(t.path);
    el.oncontextmenu = (e) => {
      e.preventDefault();
      ctxMenu(e.clientX, e.clientY, [
        { label: 'Close', fn: () => closeTab(t.path), kbd: 'Ctrl+W' },
        { label: 'Close others', fn: () => {
          for (const x of S.tabs.slice()) if (x.path !== t.path)
            closeTab(x.path); } },
        { label: 'Close all', fn: () => {
          for (const x of S.tabs.slice()) closeTab(x.path); } },
        { sep: true },
        { label: 'Copy path', fn: () =>
          window.dxn1.clipboardWrite(t.path).then(() =>
            toast('Path copied', 'ok', 1400)) },
      ]);
    };
    host.appendChild(el);
  }
  persistSession();
}

async function openFile(path, content) {
  const existing = S.tabs.find((t) => t.path === path);
  if (!existing) {
    if (content == null) {
      try { const r = await api('read_file', { path });
        content = r.content; }
      catch (err) { toast(err.message, 'err'); return; }
    }
    S.tabs.push({ path, content });
  }
  activateTab(path);
}

function activateTab(path) {
  const t = S.tabs.find((x) => x.path === path);
  if (!t) return;
  S.active = path;
  S.selected = path;
  selectRow(path);
  $('welcome').classList.add('hidden');
  $('editorWrap').classList.remove('hidden');
  const ed = $('editor');
  ed.value = t.content;
  ed.removeAttribute('readonly');
  rehighlight();
  renderTabs();
  renderStatus();
  updateGutter();
  $('stLang').textContent = langOf(path);
  $('tbTitle').textContent = basename(path) + ' — ' + S.wsName;
  setTimeout(() => ed.focus(), 10);
}

function closeTab(path) {
  const i = S.tabs.findIndex((t) => t.path === path);
  if (i < 0) return;
  const doClose = () => {
    S.tabs.splice(i, 1);
    S.dirty.delete(path);
    if (S.active === path) {
      const next = S.tabs[Math.min(i, S.tabs.length - 1)];
      if (next) activateTab(next.path);
      else {
        S.active = null;
        $('editorWrap').classList.add('hidden');
        $('welcome').classList.remove('hidden');
        $('tbTitle').textContent = S.wsName;
      }
    }
    renderTabs(); renderStatus();
  };
  if (S.dirty.has(path)) {
    confirmBox('Unsaved changes',
      basename(path) + ' has unsaved changes. Close anyway?',
      doClose, 'Discard & close');
  } else doClose();
}

function markDirty() {
  if (!S.active) return;
  const t = S.tabs.find((x) => x.path === S.active);
  if (!t) return;
  t.content = $('editor').value;
  if (!S.dirty.has(S.active)) {
    S.dirty.add(S.active);
    renderTabs();
  }
  if (S.settings.autosave) {
    clearTimeout(markDirty._t);
    markDirty._t = setTimeout(() => saveFile(true), 1500);
  }
}

async function saveFile(silent) {
  if (!S.active) { if (!silent) toast('Nothing to save', 'warn'); return; }
  const t = S.tabs.find((x) => x.path === S.active);
  if (!t) return;
  t.content = $('editor').value;
  try {
    await api('write_file', { path: t.path, content: t.content });
    S.dirty.delete(t.path);
    renderTabs();
    if (!silent) toast('Saved ' + basename(t.path), 'ok', 1500);
  } catch (err) { toast('Save failed: ' + err.message, 'err'); }
}

async function saveAll() {
  for (const p of S.dirty) { const t = S.tabs.find((x) => x.path === p);
    if (t) { try { await api('write_file', { path: p, content: t.content }); }
      catch (err) { toast('Save failed: ' + err.message, 'err'); } } }
  S.dirty.clear();
  renderTabs();
  toast('All files saved', 'ok', 1500);
}

/* ═══════════════════════════ editor ══════════════════════════════ */
const KEYWORDS = {
  python: 'def class return if elif else for while import from as with ' +
    'try except finally raise pass break continue global nonlocal lambda ' +
    'yield assert del in is not and or None True False async await match case',
  javascript: 'function return if else for while do var let const class ' +
    'extends new this typeof instanceof null undefined true false async ' +
    'await yield import export from default try catch finally throw ' +
    'switch case break continue delete void static get set of in',
  typescript: 'function return if else for while do var let const class ' +
    'extends implements interface type enum new this typeof instanceof ' +
    'null undefined true false async await yield import export from ' +
    'default try catch finally throw switch case break continue public ' +
    'private protected readonly static get set of in as satisfies',
  shell: 'if then else elif fi for while do done case esac function ' +
    'return exit local export echo cd source set shift trap',
  yaml: 'true false null yes no on off',
};
const KW_RE = (lang) => {
  const words = KEYWORDS[lang];
  return words
    ? new RegExp('\\b(' + words.split(' ').join('|') + ')\\b', 'g')
    : null;
};

function tokenize(src, lang) {
  let out = esc(src);
  const store = [];
  const keep = (html) => { store.push(html);
    return '\u0000' + (store.length - 1) + '\u0000'; };
  const pyish = lang === 'python' || lang === 'shell' ||
                lang === 'yaml';
  // comments (must run before strings may steal # inside quotes —
  // acceptable approximation for a highlighter)
  out = out.replace(pyish ? /#[^\n]*/g : /\/\/[^\n]*|\/\*[\s\S]*?\*\//g,
    (m) => keep('<span class="tk-com">' + m + '</span>'));
  // strings
  out = out.replace(/('''[\s\S]*?'''|"""[\s\S]*?"""|'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`)/g,
    (m) => keep('<span class="tk-str">' + m + '</span>'));
  // decorators / shebang
  if (pyish) out = out.replace(/(^|\n)(\s*@\w+|\s*#!\S+)/g,
    (m) => keep(m.replace(/(@\w+|#!\S+)/,
      '<span class="tk-dec">$1</span>')));
  // numbers
  out = out.replace(/\b(0x[0-9a-fA-F]+|\d+\.?\d*(?:e[+-]?\d+)?)\b/g,
    (m) => keep('<span class="tk-num">' + m + '</span>'));
  // keywords
  const kw = KW_RE(lang);
  if (kw) out = out.replace(kw,
    (m) => keep('<span class="tk-key">' + m + '</span>'));
  // function calls
  out = out.replace(/\b([a-zA-Z_]\w*)(?=\s*\()/g,
    (m) => keep('<span class="tk-fn">' + m + '</span>'));
  // restore
  out = out.replace(/\u0000(\d+)\u0000/g, (_, i) => store[+i]);
  return out;
}

function rehighlight() {
  const t = S.tabs.find((x) => x.path === S.active);
  if (!t) return;
  const lang = langOf(S.active);
  let html;
  if (lang === 'markdown') html = mdPreview(t.content);
  else html = tokenize(t.content, lang === 'plain text' ? 'plain' : lang);
  $('hlCode').innerHTML = html + '\n';
  updateGutter();
}

function mdPreview(src) {
  let h = esc(src);
  h = h.replace(/^###### (.*)$/gm, '<h6>$1</h6>')
       .replace(/^##### (.*)$/gm, '<h5>$1</h5>')
       .replace(/^#### (.*)$/gm, '<h4>$1</h4>')
       .replace(/^### (.*)$/gm, '<h3>$1</h3>')
       .replace(/^## (.*)$/gm, '<h2>$1</h2>')
       .replace(/^# (.*)$/gm, '<h1 class="tk-key">$1</h1>')
       .replace(/```([\s\S]*?)```/g,
                '<span class="tk-str">$1</span>')
       .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
       .replace(/`([^`]+)`/g, '<span class="tk-str">$1</span>')
       .replace(/^- (.*)$/gm, '<span class="tk-op">•</span> $1');
  return h;
}

function updateGutter() {
  const ed = $('editor');
  const lines = ed.value.split('\n').length;
  const cur = ed.value.slice(0, ed.selectionStart).split('\n').length;
  const g = $('gutter');
  if (g.childElementCount !== lines) {
    g.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (let i = 1; i <= lines; i++) {
      const d = document.createElement('div');
      d.textContent = i;
      frag.appendChild(d);
    }
    g.appendChild(frag);
  } else {
    [...g.children].forEach((c, i) =>
      c.classList.toggle('cur', i + 1 === cur));
  }
  // mark current line
  [...g.children].forEach((c, i) =>
    c.classList.toggle('cur', i + 1 === cur));
}

function renderStatus() {
  const ed = $('editor');
  if (!S.active) { $('stPos').textContent = '—';
    $('stLen').textContent = '—'; return; }
  const pos = ed.value.slice(0, ed.selectionStart).split('\n');
  const col = ed.selectionStart - ed.value.lastIndexOf('\n',
    ed.selectionStart - 1);
  const sel = ed.selectionEnd - ed.selectionStart;
  $('stPos').textContent = 'Ln ' + pos.length + ', Col ' + col +
    (sel > 0 ? ' (' + sel + ' sel)' : '');
  $('stLen').textContent =
    fmtSize(new Blob([ed.value]).size);
}

function editorFind(query, dir) {
  const ed = $('editor');
  if (!query) { $('findCount').textContent = '0/0'; return; }
  if (S._findQ !== query) {
    S._findQ = query;
    S.findHits = [];
    let idx = ed.value.indexOf(query);
    while (idx >= 0 && S.findHits.length < 5000) {
      S.findHits.push(idx);
      idx = ed.value.indexOf(query, idx + query.length);
    }
    S.findIdx = -1;
  }
  if (!S.findHits.length) { $('findCount').textContent = '0/0'; return; }
  S.findIdx = (S.findIdx + (dir === -1 ? -1 : 1) + S.findHits.length) %
    S.findHits.length;
  const at = S.findHits[S.findIdx];
  ed.focus();
  ed.setSelectionRange(at, at + query.length);
  const pos = ed.value.slice(0, at).split('\n');
  $('gutter').children[pos.length - 1]?.scrollIntoView
    ? $('gutter').children[pos.length - 1].scrollIntoView(
        { block: 'center' }) : null;
  $('findCount').textContent = (S.findIdx + 1) + '/' + S.findHits.length;
}

/* ══════════════════════════ terminal ═════════════════════════════ */
function termLog(msg, cls = 'tl-info') {
  const out = $('termOut');
  const line = document.createElement('div');
  line.className = cls;
  line.textContent = msg;
  out.appendChild(line);
  while (out.childElementCount > 800) out.firstChild.remove();
  out.scrollTop = out.scrollHeight;
}

async function termRun(cmdline) {
  termLog('dxn1> ' + cmdline, 'tl-accent');
  const [cmd, ...rest] = cmdline.trim().split(/\s+/);
  const arg = rest.join(' ');
  try {
    switch (cmd) {
      case '': break;
      case 'help':
        termLog('verbs: help · clear · ls · cat <file> · new <file> · rm <file> · date · echo · theme <dark|light> · accent <name> · about · run', 'tl-dim');
        break;
      case 'clear': $('termOut').innerHTML = ''; break;
      case 'ls': {
        const r = await api('tree', {});
        const names = r.entries.map((e) => e.path);
        termLog(names.length ? names.join('\n') : '(empty workspace)',
                'tl-info');
        break;
      }
      case 'cat': {
        if (!arg) { termLog('usage: cat <file>', 'tl-warn'); break; }
        const r = await api('read_file', { path: arg });
        termLog(r.content, 'tl-info');
        break;
      }
      case 'new': {
        if (!arg) { termLog('usage: new <file>', 'tl-warn'); break; }
        await createFile(arg); termLog('created ' + arg, 'tl-ok');
        break;
      }
      case 'rm': {
        if (!arg) { termLog('usage: rm <file>', 'tl-warn'); break; }
        await api('delete_path', { path: arg });
        if (S.tabs.some((t) => t.path === arg)) closeTab(arg);
        await refreshTree(true);
        termLog('deleted ' + arg, 'tl-ok');
        break;
      }
      case 'date': termLog(new Date().toString()); break;
      case 'echo': termLog(arg); break;
      case 'theme': await setMode(arg === 'light' ? 'light' : 'dark');
        termLog('theme → ' + arg, 'tl-ok'); break;
      case 'accent': await setAccent(arg || 'violet');
        termLog('accent → ' + arg, 'tl-ok'); break;
      case 'about': {
        const h = await api('hello', {});
        termLog(h.app + ' ' + h.version + ' (' + h.channel + ')' +
          ' — engine python ' + h.python, 'tl-ok');
        break;
      }
      case 'run':
        termLog('the project runner joins the engine in the next drop — everything else already works', 'tl-warn');
        break;
      default:
        termLog('unknown verb "' + cmd + '" — try help', 'tl-err');
    }
  } catch (err) { termLog(String(err.message || err), 'tl-err'); }
}

/* ══════════════════════ palette + quickopen ══════════════════════ */
function fuzzyScore(query, text) {
  if (!query) return 1;
  const q = query.toLowerCase(); const t = text.toLowerCase();
  let qi = 0, score = 0, streak = 0;
  for (let i = 0; i < t.length && qi < q.length; i++) {
    if (t[i] === q[qi]) {
      streak++; qi++;
      score += 2 + streak + (i === 0 || /[\s./_-]/.test(t[i - 1]) ? 3 : 0);
    } else streak = 0;
  }
  return qi === q.length ? score : 0;
}

const COMMANDS = [
  { label: 'New file', kbd: 'Ctrl+N', run: () => newFileFlow() },
  { label: 'Save file', kbd: 'Ctrl+S', run: () => saveFile() },
  { label: 'Save all files', kbd: 'Ctrl+Shift+S', run: () => saveAll() },
  { label: 'Quick open a file', kbd: 'Ctrl+P', run: () => openLayer('quickopen') },
  { label: 'Find in file', kbd: 'Ctrl+F', run: () => toggleFind() },
  { label: 'Close tab', kbd: 'Ctrl+W', run: () => S.active && closeTab(S.active) },
  { label: 'Tab overview', kbd: 'Ctrl+Alt+T', run: () => openOverview() },
  { label: 'Toggle terminal', kbd: 'Ctrl+`', run: () => toggleTerminal() },
  { label: 'Toggle sidebar', run: () => toggleSidebar() },
  { label: 'Open workspace…', run: async () => {
    const dir = await window.dxn1.dialog('openDirectory');
    if (!dir) return;
    try { await api('workspace_set', { workspace: dir });
      await bootEngine(); toast('Workspace opened', 'ok'); }
    catch (err) { toast(err.message, 'err'); }
  } },
  { label: 'Switch to light theme', run: () => setMode('light') },
  { label: 'Switch to dark theme', run: () => setMode('dark') },
  { label: 'Bigger editor text', kbd: 'Ctrl+=', run: () => setFont(S.settings.font + 1) },
  { label: 'Smaller editor text', kbd: 'Ctrl+-', run: () => setFont(S.settings.font - 1) },
  { label: 'Toggle word wrap', run: () => setWrap(!S.settings.wrap) },
  { label: 'Toggle autosave', run: () => setAutosave(!S.settings.autosave) },
  { label: 'Settings…', kbd: 'Ctrl+,', run: () => openSettings() },
  { label: 'Reveal workspace in file manager', run: () =>
    api('reveal', { path: '.' }).catch((e) => toast(e.message, 'err')) },
  { label: 'About DXN1 STUDIO', run: () => aboutBox() },
];

let paletteSel = 0;
function renderPalette() {
  const q = $('paletteInput').value;
  const scored = COMMANDS
    .map((c) => ({ c, s: fuzzyScore(q, c.label) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s);
  const list = $('paletteList');
  paletteSel = Math.min(paletteSel, Math.max(0, scored.length - 1));
  list.innerHTML = scored.length ? '' :
    '<div class="panel-empty">no commands match “' + esc(q) + '”</div>';
  scored.forEach(({ c }, i) => {
    const row = document.createElement('div');
    row.className = 'panel-row' + (i === paletteSel ? ' selected' : '');
    row.setAttribute('role', 'option');
    row.innerHTML = '<span class="pr-ico">◆</span>' +
      '<span class="pr-main">' + esc(c.label) + '</span>' +
      (c.kbd ? '<kbd>' + esc(c.kbd) + '</kbd>' : '');
    row.onclick = () => { closeLayer('palette'); c.run(); };
    row.onmousemove = () => { if (paletteSel !== i) {
      paletteSel = i;
      [...list.children].forEach((r, j) =>
        r.classList.toggle('selected', j === i)); } };
    list.appendChild(row);
  });
  paletteScored = scored.map((x) => x.c);
}
let paletteScored = [];

let qoSel = 0;
function renderQuickOpen() {
  const q = $('quickopenInput').value;
  const scored = S.tree
    .map((e) => ({ e, s: fuzzyScore(q, e.path) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, 60);
  const list = $('quickopenList');
  qoSel = Math.min(qoSel, Math.max(0, scored.length - 1));
  list.innerHTML = scored.length ? '' :
    '<div class="panel-empty">no files match “' + esc(q) + '”</div>';
  scored.forEach(({ e }, i) => {
    const row = document.createElement('div');
    row.className = 'panel-row' + (i === qoSel ? ' selected' : '');
    row.innerHTML = '<span class="pr-ico">' + fileIcon(e.path) +
      '</span><span class="pr-main">' + esc(basename(e.path)) +
      '</span><span class="pr-sub">' + esc(dirname(e.path) || '.') +
      '</span>';
    row.onclick = () => { closeLayer('quickopen'); openFile(e.path); };
    row.onmousemove = () => { if (qoSel !== i) { qoSel = i;
      [...list.children].forEach((r, j) =>
        r.classList.toggle('selected', j === i)); } };
    list.appendChild(row);
  });
  qoScored = scored.map((x) => x.e);
}
let qoScored = [];

function newFileFlow() {
  promptBox('New file', 'name.py  (a real file in the workspace)', '',
    (name) => createFile(name));
}

/* ══════════════════════════ overview ═════════════════════════════ */
let ovSel = 0;
function openOverview() {
  if (!S.tabs.length) { toast('No open tabs', 'info', 1500); return; }
  $('ovFilter').value = '';
  openLayer('overview');
  ovSel = Math.max(0, S.tabs.findIndex((t) => t.path === S.active));
  renderOverview();
}
function renderOverview() {
  const q = $('ovFilter').value.toLowerCase();
  const tabs = S.tabs.filter((t) => t.path.toLowerCase().includes(q));
  $('ovCount').textContent = tabs.length + ' open';
  const grid = $('ovGrid');
  grid.innerHTML = tabs.length ? '' :
    '<div class="panel-empty">no tabs match</div>';
  ovSel = Math.min(ovSel, Math.max(0, tabs.length - 1));
  tabs.forEach((t, i) => {
    const card = document.createElement('div');
    card.className = 'ov-card' + (i === ovSel ? ' selected' : '');
    card.innerHTML =
      '<div class="ov-name">' +
      (S.dirty.has(t.path) ? '<span class="ov-dirty">●</span> ' : '') +
      esc(basename(t.path)) + '</div>' +
      '<div class="ov-dir">' + esc(dirname(t.path) || '.') + '</div>' +
      (t.path === S.active ? '<span class="ov-badge">ACTIVE</span>' : '') +
      '<button class="ov-x" aria-label="Close tab">✕</button>';
    card.onclick = (e) => {
      if (e.target.classList.contains('ov-x')) return;
      closeLayer('overview'); activateTab(t.path);
    };
    card.querySelector('.ov-x').onclick = () => {
      closeTab(t.path); renderOverview(); };
    grid.appendChild(card);
  });
  ovShown = tabs;
}
let ovShown = [];

/* ═════════════════════════ settings ══════════════════════════════ */
function applyTheme() {
  document.documentElement.dataset.mode = S.settings.mode;
  document.documentElement.dataset.accent = S.settings.accent;
  document.documentElement.style.setProperty('--editor-font',
    S.settings.font + 'px');
  document.body.classList.toggle('wrap-on', S.settings.wrap);
  $('editor').setAttribute('wrap', S.settings.wrap ? 'soft' : 'off');
  $('stTheme').textContent = '◐ ' + S.settings.mode;
  document.querySelectorAll('#setMode .seg-btn').forEach((b) =>
    b.classList.toggle('active', b.dataset.mode === S.settings.mode));
  document.querySelectorAll('#setAccent .swatch').forEach((b) =>
    b.classList.toggle('active', b.dataset.accent === S.settings.accent));
  $('setAutosave').checked = S.settings.autosave;
  $('setWrap').checked = S.settings.wrap;
  $('fontVal').textContent = S.settings.font;
  LS.set('dxn1-settings', S.settings);
  rehighlight(); updateGutter();
}
function setMode(m) { S.settings.mode = m; applyTheme(); }
function setAccent(a) { if (a) { S.settings.accent = a; applyTheme(); } }
function setFont(f) {
  S.settings.font = Math.max(10, Math.min(22, f)); applyTheme();
}
function setWrap(w) { S.settings.wrap = w; applyTheme(); }
function setAutosave(a) { S.settings.autosave = a; applyTheme(); }

function openSettings() { openLayer('settings'); }

const ACCENT_LIST = ['violet', 'cyan', 'green', 'orange', 'rose', 'blue'];
function buildSettings() {
  const sw = $('setAccent');
  sw.innerHTML = '';
  for (const a of ACCENT_LIST) {
    const b = document.createElement('button');
    b.className = 'swatch';
    b.dataset.accent = a;
    b.setAttribute('aria-label', 'Accent ' + a);
    b.style.background = getComputedStyle(document.documentElement)
      .getPropertyValue('--accent');
    b.onclick = () => setAccent(a);
    sw.appendChild(b);
  }
  // colour each swatch with its own accent
  const map = { violet: '#8b5cf6', cyan: '#22d3ee', green: '#4ade80',
                orange: '#fb923c', rose: '#fb7185', blue: '#60a5fa' };
  [...sw.children].forEach((b) => {
    b.style.background = map[b.dataset.accent];
  });
  document.querySelectorAll('#setMode .seg-btn').forEach((b) =>
    b.onclick = () => setMode(b.dataset.mode));
  $('fontPlus').onclick = () => setFont(S.settings.font + 1);
  $('fontMinus').onclick = () => setFont(S.settings.font - 1);
  $('setAutosave').onchange = (e) => setAutosave(e.target.checked);
  $('setWrap').onchange = (e) => setWrap(e.target.checked);
  $('settingsClose').onclick = () => closeLayer('settings');
}

function aboutBox() {
  api('hello', {}).then((h) => {
    confirmBox('About DXN1 STUDIO',
      h.app + ' v' + h.version + ' (' + h.channel + ')' +
      '\nengine: python ' + h.python +
      '\nshell: electron ' + window.dxn1.electron +
      '\nworkspace: ' + h.workspace,
      () => {}, 'Close');
    $('modalOk').textContent = 'Close';
  }).catch(() => {});
}

/* ═══════════════════════ context menu ════════════════════════════ */
function ctxMenu(x, y, items) {
  const m = $('ctxmenu');
  m.innerHTML = '';
  for (const it of items) {
    if (it.sep) { const s = document.createElement('div');
      s.className = 'ctx-sep'; m.appendChild(s); continue; }
    const el = document.createElement('div');
    el.className = 'ctx-item' + (it.danger ? ' danger' : '');
    el.setAttribute('role', 'menuitem');
    el.innerHTML = esc(it.label) + (it.kbd ? '<kbd>' +
      esc(it.kbd) + '</kbd>' : '');
    el.onclick = () => { hideCtx(); it.fn(); };
    m.appendChild(el);
  }
  m.classList.remove('hidden');
  const r = m.getBoundingClientRect();
  m.style.left = Math.min(x, window.innerWidth - r.width - 8) + 'px';
  m.style.top = Math.min(y, window.innerHeight - r.height - 8) + 'px';
}
function hideCtx() {
  const m = $('ctxmenu');
  const was = !m.classList.contains('hidden');
  m.classList.add('hidden');
  return was;
}

/* ══════════════════════════ toggles ══════════════════════════════ */
function toggleTerminal() {
  $('terminalPanel').classList.toggle('collapsed');
  if (!$('terminalPanel').classList.contains('collapsed'))
    $('termInput').focus();
}
function toggleSidebar() { $('sidebar').classList.toggle('collapsed'); }
function toggleFind() {
  const fb = $('findbar');
  fb.classList.toggle('hidden');
  if (!fb.classList.contains('hidden')) { $('findInput').focus();
    $('findInput').select(); }
  else { S._findQ = null; $('editor').focus(); }
}

function switchView(view) {
  document.querySelectorAll('.act[data-view]').forEach((b) =>
    b.classList.toggle('active', b.dataset.view === view));
  if (view === 'palette') { openLayer('palette'); return; }
  if (view === 'tools') { toggleTerminal(); return; }
  $('sidebar').classList.remove('collapsed');
  $('sbTitle').firstChild.textContent =
    view === 'search' ? 'SEARCH' : 'EXPLORER';
  $('view-explorer').classList.toggle('hidden', view !== 'explorer');
  $('view-search').classList.toggle('hidden', view !== 'search');
  if (view === 'search') $('searchInput').focus();
}

/* ════════════════════════════ search ═════════════════════════════ */
let searchTimer = null;
function scheduleSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 260);
}
async function runSearch() {
  const q = $('searchInput').value;
  const host = $('searchResults');
  if (!q || q.length < 2) { host.innerHTML = ''; return; }
  host.innerHTML = '<div class="panel-empty">searching…</div>';
  const out = [];
  try {
    for (const e of S.tree.slice(0, 600)) {
      if (e.size > 1048576) continue;
      let r;
      try { r = await api('read_file', { path: e.path }); }
      catch (_) { continue; }
      const lines = r.content.split('\n');
      let hits = 0;
      for (let i = 0; i < lines.length && hits < 5; i++) {
        const at = lines[i].toLowerCase().indexOf(q.toLowerCase());
        if (at >= 0) {
          hits++;
          out.push({ path: e.path, line: i + 1, text: lines[i] });
        }
      }
      if (out.length > 80) break;
    }
  } catch (err) { host.innerHTML = '<div class="panel-empty">' +
    esc(err.message) + '</div>'; return; }
  host.innerHTML = '';
  let lastFile = null;
  for (const h of out) {
    if (h.path !== lastFile) {
      lastFile = h.path;
      const f = document.createElement('div');
      f.className = 'sr-file';
      f.innerHTML = fileIcon(h.path) + ' <b>' + esc(basename(h.path)) +
        '</b> <span style="color:var(--muted)">' +
        esc(dirname(h.path) || '.') + '</span>';
      f.onclick = () => openFile(h.path);
      host.appendChild(f);
    }
    const row = document.createElement('div');
    row.className = 'sr-line';
    const idx = h.text.toLowerCase().indexOf(q.toLowerCase());
    row.innerHTML = 'Ln ' + h.line + ': ' +
      esc(h.text.slice(Math.max(0, idx - 24), idx)) + '<mark>' +
      esc(h.text.slice(idx, idx + q.length)) + '</mark>' +
      esc(h.text.slice(idx + q.length, idx + q.length + 40));
    row.onclick = () => openFile(h.path);
    host.appendChild(row);
  }
  if (!out.length) host.innerHTML =
    '<div class="panel-empty">no matches across ' + S.tree.length +
    ' files</div>';
}

/* ═════════════════════════ session ═══════════════════════════════ */
function persistSession() {
  LS.set('dxn1-session', { tabs: S.tabs.map((t) => t.path),
    active: S.active });
}

/* ════════════════════════════ boot ═══════════════════════════════ */
function wireEvents() {
  // window controls
  $('winMin').onclick = () => window.dxn1.win('minimize');
  $('winMax').onclick = () => window.dxn1.win('maximize');
  $('winClose').onclick = () => window.dxn1.win('close');
  window.dxn1.winState((s) => $('winMax').setAttribute('data-tip',
    s === 'maximized' ? 'Restore' : 'Maximize'));

  // activity bar
  document.querySelectorAll('.act[data-view]').forEach((b) =>
    b.onclick = () => switchView(b.dataset.view));
  $('actSettings').onclick = () => openSettings();

  // sidebar actions
  $('sbNewFile').onclick = () => newFileFlow();
  $('sbRefresh').onclick = () => refreshTree();

  // tabs
  $('btnOverview').onclick = () => openOverview();

  // find bar
  $('findInput').addEventListener('input', () => { S._findQ = null;
    editorFind($('findInput').value, 1); });
  $('findNext').onclick = () => editorFind($('findInput').value, 1);
  $('findPrev').onclick = () => editorFind($('findInput').value, -1);
  $('findClose').onclick = () => toggleFind();
  $('findInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault();
      editorFind($('findInput').value, e.shiftKey ? -1 : 1); }
    if (e.key === 'Escape') { e.stopPropagation(); toggleFind(); }
  });

  // editor
  const ed = $('editor');
  ed.addEventListener('input', () => { markDirty(); rehighlight(); });
  ed.addEventListener('scroll', () => {
    // keep layers glued (textarea never scrolls itself, this is a safety net)
    $('highlight').scrollTop = ed.scrollTop;
    $('highlight').scrollLeft = ed.scrollLeft;
  });
  document.addEventListener('selectionchange', () => {
    if (document.activeElement === ed) { renderStatus(); updateGutter(); }
  });
  ed.addEventListener('keydown', (e) => {
    if (e.key === 'Tab' && !e.shiftKey) {
      e.preventDefault();
      const s = ed.selectionStart;
      ed.setRangeText('    ', s, ed.selectionEnd, 'end');
      markDirty(); rehighlight();
    }
    if (e.key === 'Enter') { // keep simple indent: copy leading spaces
      const s = ed.selectionStart;
      const lineStart = ed.value.lastIndexOf('\n', s - 1) + 1;
      const indent = (ed.value.slice(lineStart, s).match(/^\s*/) || [''])[0];
      if (indent) {
        e.preventDefault();
        ed.setRangeText('\n' + indent, s, ed.selectionEnd, 'end');
        markDirty(); rehighlight();
      }
    }
  });

  // terminal
  $('termToggle').onclick = () => toggleTerminal();
  $('termClear').onclick = () => { $('termOut').innerHTML = ''; };
  const ti = $('termInput');
  ti.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const v = ti.value; ti.value = '';
      if (v.trim()) { S.termHistory.push(v); S.termHidx =
        S.termHistory.length; }
      termRun(v);
    } else if (e.key === 'ArrowUp') {
      if (S.termHidx > 0) { S.termHidx--;
        ti.value = S.termHistory[S.termHidx] || ''; }
      e.preventDefault();
    } else if (e.key === 'ArrowDown') {
      if (S.termHidx < S.termHistory.length - 1) { S.termHidx++;
        ti.value = S.termHistory[S.termHidx] || ''; }
      else { S.termHidx = S.termHistory.length; ti.value = ''; }
      e.preventDefault();
    }
  });

  // palette + quickopen inputs
  $('paletteInput').addEventListener('input', () => { paletteSel = 0;
    renderPalette(); });
  $('paletteInput').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); paletteSel =
      Math.min(paletteSel + 1, paletteScored.length - 1);
      renderPalette(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); paletteSel =
      Math.max(paletteSel - 1, 0); renderPalette(); }
    else if (e.key === 'Enter') { e.preventDefault();
      const c = paletteScored[paletteSel];
      if (c) { closeLayer('palette'); c.run(); } }
    else if (e.key === 'Escape') { e.stopPropagation();
      closeLayer('palette'); }
  });
  $('quickopenInput').addEventListener('input', () => { qoSel = 0;
    renderQuickOpen(); });
  $('quickopenInput').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); qoSel =
      Math.min(qoSel + 1, qoScored.length - 1); renderQuickOpen(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); qoSel =
      Math.max(qoSel - 1, 0); renderQuickOpen(); }
    else if (e.key === 'Enter') { e.preventDefault();
      const f = qoScored[qoSel];
      if (f) { closeLayer('quickopen'); openFile(f.path); } }
    else if (e.key === 'Escape') { e.stopPropagation();
      closeLayer('quickopen'); }
  });

  // overview
  $('ovFilter').addEventListener('input', () => { ovSel = 0;
    renderOverview(); });
  $('ovFilter').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && ovShown[ovSel]) {
      closeLayer('overview'); activateTab(ovShown[ovSel].path); }
    if (e.key === 'ArrowDown') { e.preventDefault(); ovSel =
      Math.min(ovSel + 1, ovShown.length - 1); renderOverview(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); ovSel =
      Math.max(ovSel - 1, 0); renderOverview(); }
    if (e.key === 'Escape') { e.stopPropagation();
      closeLayer('overview'); }
  });

  // modal
  $('modalOk').onclick = () => { closeLayer('modal');
    const cb = modalCb; modalCb = null; if (cb) cb(); };
  $('modalCancel').onclick = () => { modalCb = null;
    closeLayer('modal'); };

  // overlay click-through: click on the dim closes the top layer
  $('overlay').addEventListener('mousedown', () => {
    if (document.getElementById('promptDialog')) return;
    modalCb = null;
    closeTopLayer();
  });

  // search
  $('searchInput').addEventListener('input', scheduleSearch);

  // statusbar
  $('stTheme').onclick = () =>
    setMode(S.settings.mode === 'dark' ? 'light' : 'dark');

  // context menu dismiss + global keys
  document.addEventListener('mousedown', (e) => {
    if (!$('ctxmenu').contains(e.target)) hideCtx();
  });
  document.addEventListener('keydown', (e) => {
    const mod = e.ctrlKey || e.metaKey;
    const inField = /^(INPUT|TEXTAREA)$/.test(
      document.activeElement && document.activeElement.tagName || '');
    if (e.key === 'Escape') {
      if (hideCtx()) return;
      if (closeTopLayer()) return;
      return;
    }
    if (!mod) return;
    const k = e.key.toLowerCase();
    if (k === 'k' || (k === 'p' && e.shiftKey)) {
      e.preventDefault(); paletteSel = 0;
      $('paletteInput').value = ''; renderPalette();
      $('palette').classList.contains('hidden')
        ? openLayer('palette') : closeLayer('palette');
    } else if (k === 'p') {
      e.preventDefault(); qoSel = 0;
      $('quickopenInput').value = ''; renderQuickOpen();
      openLayer('quickopen');
    } else if (k === 'n') { e.preventDefault(); newFileFlow(); }
    else if (k === 's' && e.shiftKey) { e.preventDefault(); saveAll(); }
    else if (k === 's') { e.preventDefault(); saveFile(); }
    else if (k === 'w') { e.preventDefault();
      if (S.active) closeTab(S.active); }
    else if (k === 'f' && S.active) { e.preventDefault(); toggleFind(); }
    else if (k === ',') { e.preventDefault(); openSettings(); }
    else if (k === 't' && e.altKey) { e.preventDefault();
      openOverview(); }
    else if (k === '=') { e.preventDefault(); setFont(S.settings.font + 1); }
    else if (k === '-') { e.preventDefault(); setFont(S.settings.font - 1); }
    else if (e.key === '`') { e.preventDefault(); toggleTerminal(); }
  });

  // sidebar resize
  const grip = $('gutterResize');
  grip.addEventListener('mousedown', (e) => {
    e.preventDefault();
    grip.classList.add('active');
    const move = (ev) => {
      const w = Math.min(480, Math.max(170, ev.clientX - 46));
      document.documentElement.style.setProperty('--sb-w', w + 'px');
    };
    const up = () => { grip.classList.remove('active');
      document.removeEventListener('mousemove', move);
      document.removeEventListener('mouseup', up); };
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', up);
  });

  // bridge lifecycle
  window.dxn1.onBridgeUp((info) => {
    S.bridge = true; S.demo = false;
    S.ws = info.workspace; S.wsName = basename(info.workspace) ||
      info.workspace;
    $('chipDemo').classList.add('hidden');
    $('welcomeDemo').classList.add('hidden');
    $('termPrompt').textContent = 'dxn1>';
    bootWorkspace(info);
  });
  window.dxn1.onBridgeDead(({ reason }) => {
    if (S.demo) return;
    S.demo = true;
    $('chipDemo').classList.remove('hidden');
    $('welcomeDemo').classList.remove('hidden');
    $('tbTitle').textContent = 'demo workspace — engine offline';
    $('chipWorkspace').textContent = '◆ demo';
    termLog('engine offline (' + reason + ') — demo workspace active',
            'tl-warn');
    bootWorkspace(null);
  });
}

async function bootWorkspace(info) {
  await refreshTree();
  // restore session tabs that still exist
  const ses = LS.get('dxn1-session', null);
  const known = new Set(S.tree.map((e) => e.path));
  if (ses && Array.isArray(ses.tabs)) {
    for (const p of ses.tabs) {
      if (known.has(p)) {
        try { const r = await api('read_file', { path: p });
          S.tabs.push({ path: p, content: r.content }); }
        catch (_) {}
      }
    }
    const act = ses.active && known.has(ses.active) ? ses.active
      : (S.tabs[0] && S.tabs[0].path);
    if (act) { activateTab(act); return; }
  }
  renderTabs(); renderStatus();
}

async function bootEngine() {
  const h = await api('hello', {});
  S.ws = h.workspace;
  S.wsName = basename(h.workspace) || h.workspace;
  $('chipWorkspace').textContent = '◆ ' + S.wsName;
  termLog('engine up — ' + h.app + ' v' + h.version + ' (' + h.channel +
    '), python ' + h.python, 'tl-ok');
  await bootWorkspace(h);
}

function boot() {
  const saved = LS.get('dxn1-settings', null);
  if (saved) Object.assign(S.settings, saved);
  buildSettings();
  applyTheme();
  wireEvents();
  termLog('DXN1 STUDIO shell ready — waiting for the engine…', 'tl-dim');
  // if no bridge event arrives quickly, go demo so nothing is dead
  setTimeout(() => {
    if (!S.bridge && !S.demo) {
      window.dxn1.request('hello', {}).then(() => bootEngine())
        .catch(() => {
          S.demo = true;
          $('chipDemo').classList.remove('hidden');
          $('welcomeDemo').classList.remove('hidden');
          $('tbTitle').textContent = 'demo workspace — engine offline';
          $('chipWorkspace').textContent = '◆ demo';
          termLog('engine unreachable — demo workspace active', 'tl-warn');
          bootWorkspace(null);
        });
    }
  }, 1200);
}

document.addEventListener('DOMContentLoaded', boot);
