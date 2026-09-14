"""DS2 SQLite Lab — browse, schema-dive and query any SQLite database.

Read-only by default (the lab never mutates your data unless you flip
the read-write toggle). Engines are pure and unit-tested; the window is
defensive — any failure lands in the status bar, never in a crash.

Engine
------
connect / list_tables / table_columns / table_indexes / sample_rows /
run_query / export_csv / markdown_table / db_info / find_databases

Window
------
SQLiteLab: tables sidebar, Browse / Schema / Query / Info tabs,
CSV export, markdown copy, read-only ↔ read-write reconnect.

Open with: palette, Workshop menu, terminal ``db`` / ``sqlite``,
or ``db <path-to-file>``.
"""

import csv
import os
import sqlite3
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

__all__ = [
    "connect", "list_tables", "table_columns", "table_indexes",
    "sample_rows", "run_query", "export_csv", "markdown_table",
    "db_info", "human_size", "find_databases", "qident",
    "SQLiteLab", "open_sqlitelab",
]

DB_EXTS = {".db", ".sqlite", ".sqlite3", ".db3"}
CELL_CAP = 160          # chars shown per cell in the grids
QUERY_CAP = 500         # rows fetched per query run
FIND_LIMIT = 25         # databases auto-discovered per workspace


# ---------------------------------------------------------------- engine

def qident(name):
    """Quote an SQLite identifier safely (doubles inner quotes)."""
    return '"' + str(name).replace('"', '""') + '"'


def human_size(n):
    """1234567 -> '1.2 MB' (decimal units, one decimal)."""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def connect(path, read_only=True):
    """Open *path*; read-only via URI mode when possible.

    Returns the sqlite3 connection. Raises sqlite3.Error on failure.
    """
    path = os.path.abspath(path)
    if read_only:
        uri = "file:" + path.replace("?", "%3f").replace("#", "%23") + "?mode=ro"
        try:
            return sqlite3.connect(uri, uri=True)
        except sqlite3.Error:
            # older builds / odd paths: fall back to plain open
            return sqlite3.connect(path)
    return sqlite3.connect(path)


def _count_rows(conn, table):
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM {qident(table)}")
        return cur.fetchone()[0]
    except sqlite3.Error:
        return None


def list_tables(conn):
    """User tables + views as dicts: name, kind, rows (None if unknown)."""
    out = []
    try:
        cur = conn.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name")
        rows = cur.fetchall()
    except sqlite3.Error:
        return out
    for name, kind in rows:
        out.append({"name": name,
                    "kind": kind or "table",
                    "rows": None if kind == "view" else _count_rows(conn, name)})
    return out


def table_columns(conn, table):
    """PRAGMA table_info → dicts cid/name/type/notnull/dflt_value/pk."""
    cols = []
    try:
        cur = conn.execute(f"PRAGMA table_info({qident(table)})")
        for cid, name, ctype, notnull, dflt, pk in cur.fetchall():
            cols.append({"cid": cid, "name": name,
                         "type": ctype or "", "notnull": bool(notnull),
                         "dflt_value": dflt, "pk": int(pk or 0)})
    except sqlite3.Error:
        pass
    return cols


def table_indexes(conn, table):
    """Indexes on *table* → dicts name/unique/origin/cols."""
    out = []
    try:
        ilist = conn.execute(
            f"PRAGMA index_list({qident(table)})").fetchall()
    except sqlite3.Error:
        return out
    for row in ilist:
        # (seq, name, unique, origin, partial) on modern sqlite
        if len(row) >= 4:
            _seq, name, unique, origin = row[0], row[1], row[2], row[3]
        else:  # pragma: no cover — ancient sqlite
            name, unique, origin = row[1], row[2], ""
        cols = []
        try:
            for row in conn.execute(
                    f"PRAGMA index_info({qident(name)})").fetchall():
                cols.append(row[-1])   # (seqno, cid, name) — name last
        except sqlite3.Error:
            pass
        out.append({"name": name, "unique": bool(unique),
                    "origin": origin or "c", "cols": cols})
    return out


def _cell(v):
    """Render one cell for display (bytes, long text, None)."""
    if v is None:
        return "NULL"
    if isinstance(v, bytes):
        return f"<{len(v)} bytes>"
    s = str(v)
    if len(s) > CELL_CAP:
        s = s[: CELL_CAP - 1] + "…"
    return s


def sample_rows(conn, table, limit=200):
    """(columns, rows-as-display-strings) for the Browse grid."""
    try:
        cur = conn.execute(
            f"SELECT * FROM {qident(table)} LIMIT {int(limit)}")
        cols = [d[0] for d in cur.description or []]
        rows = [[_cell(v) for v in tup] for tup in cur.fetchall()]
    except sqlite3.Error as exc:
        return [], [], str(exc)
    return cols, rows, ""


def run_query(conn, sql, cap=QUERY_CAP):
    """Execute one statement → result dict.

    kind='rows' → columns/rows (display-truncated, ≤ cap)
    kind='ok'   → statement ran, affected count
    kind='error'→ message (engine never raises)
    """
    res = {"kind": "error", "columns": [], "rows": [],
           "affected": 0, "elapsed_ms": 0, "error": ""}
    t0 = time.perf_counter()
    try:
        cur = conn.execute(sql)
        conn.commit()
    except sqlite3.Error as exc:
        res["error"] = str(exc)
        res["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
        return res
    res["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
    if cur.description is None:
        res["kind"] = "ok"
        res["affected"] = max(cur.rowcount, 0)
        return res
    res["kind"] = "rows"
    res["columns"] = [d[0] for d in cur.description]
    try:
        for tup in cur.fetchmany(cap):
            res["rows"].append([_cell(v) for v in tup])
    except sqlite3.Error as exc:
        res["kind"] = "error"
        res["error"] = str(exc)
    return res


def export_csv(columns, rows, path):
    """Write rows (lists of strings) to *path*; returns row count."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        for r in rows:
            w.writerow(r)
    return len(rows)


def markdown_table(columns, rows, max_rows=50):
    """GitHub-style markdown table; caps rows and says so."""
    def esc(v):
        return str(v).replace("|", "\\|").replace("\n", " ")
    head = "| " + " | ".join(esc(c) for c in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [head, sep]
    for r in rows[:max_rows]:
        lines.append("| " + " | ".join(esc(v) for v in r) + " |")
    if len(rows) > max_rows:
        lines.append(f"… {len(rows) - max_rows} more rows not shown")
    return "\n".join(lines)


def db_info(conn):
    """(label, value) pairs describing the database file."""
    info = []
    info.append(("SQLite version", sqlite3.sqlite_version))
    try:
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        pages = conn.execute("PRAGMA page_count").fetchone()[0]
        freelist = conn.execute("PRAGMA freelist_count").fetchone()[0]
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        enc = conn.execute("PRAGMA encoding").fetchone()[0]
        info.append(("File size (data)", human_size(page_size * pages)))
        info.append(("Page size", f"{page_size} B × {pages:,} pages"))
        info.append(("Free pages", f"{freelist:,}"))
        info.append(("Journal mode", str(journal)))
        info.append(("Encoding", str(enc)))
    except sqlite3.Error as exc:
        info.append(("Introspection", f"failed: {exc}"))
    try:
        tabs = conn.execute(
            "SELECT type, COUNT(*) FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' GROUP BY type").fetchall()
        for kind, n in tabs:
            info.append((f"{kind}s", str(n)))
    except sqlite3.Error:
        pass
    return info


def find_databases(root, limit=FIND_LIMIT):
    """Workspace scan for *.db/*.sqlite* files (skips junk dirs)."""
    skip = {"__pycache__", ".git", ".hg", ".svn", "node_modules",
            ".venv", "venv", ".dx1", ".idea", ".vscode", "dist",
            "build", ".mypy_cache", ".pytest_cache", ".tox",
            "site-packages", ".terraform"}
    found = []
    if not root or not os.path.isdir(root):
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in DB_EXTS:
                found.append(os.path.join(dirpath, name))
                if len(found) >= limit:
                    return found
    return sorted(found)


# ---------------------------------------------------------------- window

class SQLiteLab(tk.Toplevel):
    """Read-mostly SQLite browser with a query bench."""

    def __init__(self, parent, theme, db_path="", workspace=""):
        super().__init__(parent)
        self.theme = theme or {}
        self.workspace = workspace
        self.db_path = ""
        self.conn = None
        self.read_only = tk.BooleanVar(value=True)
        self._last_result = None      # (columns, rows) for export
        self._clock_job = None

        t = self.theme
        self.title("SQLite Lab — DXN1 STUDIO")
        self.configure(bg=t.get("bg", "#16161e"))
        self.geometry("1000x640")
        self.minsize(760, 480)
        try:
            self.transient(parent)
        except Exception:
            pass

        self._build_style()
        self._build_toolbar()
        body = tk.Frame(self, bg=t.get("bg", "#16161e"))
        body.pack(fill=tk.BOTH, expand=True)
        self._build_sidebar(body)
        self._build_notebook(body)
        self._build_statusbar()

        self.bind("<F5>", lambda _e: self.run_current_query())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self._close)

        if db_path and os.path.isfile(db_path):
            self.load_db(db_path)
        elif workspace:
            hits = find_databases(workspace)
            if hits:
                self.set_status(f"{len(hits)} database(s) in the workspace"
                                " — double-click one in the sidebar")
                self._fill_picker(hits)
            else:
                self.set_status("No .db / .sqlite files found in the "
                                "workspace — use Open…")

    # ---------------------------------------------------------- style
    def _build_style(self):
        t = self.theme
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self._style_seed = f"sqlab{id(self)}"
        base = dict(background=t.get("editor", "#1b1b24"),
                    fieldbackground=t.get("editor", "#1b1b24"),
                    foreground=t.get("text", "#e8e8f0"),
                    rowheight=22, borderwidth=0)
        style.configure(f"{self._style_seed}.Treeview", **base)
        style.configure(f"{self._style_seed}.Treeview.Heading",
                        background=t.get("header", "#242432"),
                        foreground=t.get("text", "#e8e8f0"),
                        relief="flat")
        style.map(f"{self._style_seed}.Treeview",
                  background=[("selected", t.get("hover", "#2c2c3e"))])

    # ---------------------------------------------------------- chrome
    def _build_toolbar(self):
        t = self.theme
        bar = tk.Frame(self, bg=t.get("header", "#242432"))
        bar.pack(fill=tk.X)
        self.path_lbl = tk.Label(
            bar, text="No database loaded", anchor="w",
            bg=t.get("header", "#242432"),
            fg=t.get("text_muted", "#8a8a9a"), font=("TkDefaultFont", 10))
        self.path_lbl.pack(side=tk.LEFT, padx=(12, 6), pady=6)

        def _btn(text, cmd):
            return tk.Button(
                bar, text=text, command=cmd, relief="flat",
                bg=t.get("hover", "#2c2c3e"), fg=t.get("text", "#e8e8f0"),
                activebackground=t.get("border", "#3a3a4e"),
                activeforeground=t.get("text", "#e8e8f0"), padx=10, pady=2,
                cursor="hand2", bd=0)

        _btn("Open…", self.pick_db).pack(side=tk.LEFT, padx=3, pady=5)
        _btn("Refresh", self.refresh).pack(side=tk.LEFT, padx=3, pady=5)
        self.rw_btn = _btn("read-only ✓", self.toggle_readonly)
        self.rw_btn.pack(side=tk.RIGHT, padx=8, pady=5)

    def _build_sidebar(self, parent):
        t = self.theme
        left = tk.Frame(parent, bg=t.get("bg", "#16161e"))
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 4), pady=8)
        tk.Label(left, text="TABLES & VIEWS", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(0, 4))
        self.tables_tv = ttk.Treeview(
            left, columns=("kind", "rows"), show="tree headings",
            height=24, style=self._style_seed + ".Treeview")
        self.tables_tv.heading("#0", text="name")
        self.tables_tv.heading("kind", text="kind")
        self.tables_tv.heading("rows", text="rows")
        self.tables_tv.column("#0", width=170, stretch=True)
        self.tables_tv.column("kind", width=54, anchor="center")
        self.tables_tv.column("rows", width=60, anchor="e")
        self.tables_tv.pack(fill=tk.Y, expand=True)
        self.tables_tv.tag_configure("view", foreground=t.get(
            "text_muted", "#8a8a9a"))
        self.tables_tv.bind("<Double-1>", self._on_table_open)
        self.tables_tv.bind("<<TreeviewSelect>>", self._on_table_select)

    def _build_notebook(self, parent):
        t = self.theme
        self.nb = ttk.Notebook(parent)
        self.nb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                     padx=(4, 8), pady=8)

        # ---- Browse tab
        browse = tk.Frame(self.nb, bg=t.get("bg", "#16161e"))
        self.nb.add(browse, text=" Browse ")
        tools = tk.Frame(browse, bg=t.get("bg", "#16161e"))
        tools.pack(fill=tk.X, pady=(4, 2))
        tk.Label(tools, text="limit", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(side=tk.LEFT,
                                                         padx=(4, 2))
        self.limit_var = tk.StringVar(value="200")
        tk.Spinbox(tools, values=("50", "200", "500", "1000", "5000"),
                   width=6, textvariable=self.limit_var,
                   command=self.reload_current_table,
                   bg=t.get("editor", "#1b1b24"),
                   fg=t.get("text", "#e8e8f0"),
                   buttonbackground=t.get("hover", "#2c2c3e"),
                   relief="flat", insertbackground=t.get(
                       "text", "#e8e8f0")).pack(side=tk.LEFT)
        self._mk_btn(tools, "Export CSV", self.export_current_csv).pack(
            side=tk.LEFT, padx=6)
        self._mk_btn(tools, "Copy as Markdown", self.copy_current_md).pack(
            side=tk.LEFT, padx=2)
        self.browse_tv = ttk.Treeview(
            browse, show="headings", height=20,
            style=self._style_seed + ".Treeview")
        self.browse_tv.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        bb = tk.Frame(browse, bg=t.get("bg", "#16161e"))
        bb.pack(fill=tk.X)
        self.browse_status = tk.Label(
            bb, text="double-click a table to browse", anchor="w",
            bg=t.get("bg", "#16161e"),
            fg=t.get("text_muted", "#8a8a9a"))
        self.browse_status.pack(side=tk.LEFT, padx=6, pady=2)

        # ---- Schema tab
        schema = tk.Frame(self.nb, bg=t.get("bg", "#16161e"))
        self.nb.add(schema, text=" Schema ")
        tk.Label(schema, text="COLUMNS", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w",
                                                         padx=6, pady=(6, 2))
        self.cols_tv = ttk.Treeview(
            schema, columns=("type", "null", "dflt", "pk"),
            show="tree headings", height=10,
            style=self._style_seed + ".Treeview")
        self.cols_tv.heading("#0", text="name")
        self.cols_tv.heading("type", text="type")
        self.cols_tv.heading("null", text="null?")
        self.cols_tv.heading("dflt", text="default")
        self.cols_tv.heading("pk", text="pk")
        self.cols_tv.column("#0", width=150)
        self.cols_tv.column("type", width=90)
        self.cols_tv.column("null", width=54, anchor="center")
        self.cols_tv.column("dflt", width=90)
        self.cols_tv.column("pk", width=34, anchor="center")
        self.cols_tv.pack(fill=tk.BOTH, expand=True, padx=6)
        tk.Label(schema, text="INDEXES", bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a"),
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w",
                                                         padx=6, pady=(8, 2))
        self.idx_tv = ttk.Treeview(
            schema, columns=("cols", "flags"), show="tree headings",
            height=6, style=self._style_seed + ".Treeview")
        self.idx_tv.heading("#0", text="name")
        self.idx_tv.heading("cols", text="columns")
        self.idx_tv.heading("flags", text="flags")
        self.idx_tv.column("#0", width=170)
        self.idx_tv.column("cols", width=200)
        self.idx_tv.column("flags", width=110, anchor="center")
        self.idx_tv.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # ---- Query tab
        query = tk.Frame(self.nb, bg=t.get("bg", "#16161e"))
        self.nb.add(query, text=" Query ")
        qbar = tk.Frame(query, bg=t.get("bg", "#16161e"))
        qbar.pack(fill=tk.X, pady=(4, 2))
        self._mk_btn(qbar, "Run  (F5)", self.run_current_query).pack(
            side=tk.LEFT, padx=4)
        tk.Label(qbar, text="one statement · SELECT for a grid",
                 bg=t.get("bg", "#16161e"),
                 fg=t.get("text_muted", "#8a8a9a")).pack(side=tk.LEFT,
                                                         padx=6)
        self.sql_txt = tk.Text(
            query, height=6, wrap="word", relief="flat",
            bg=t.get("editor", "#1b1b24"), fg=t.get("text", "#e8e8f0"),
            insertbackground=t.get("text", "#e8e8f0"),
            undo=True, font=("TkFixedFont", 10))
        self.sql_txt.pack(fill=tk.X, padx=6, pady=4)
        self.sql_txt.insert("1.0", "SELECT name, sql FROM sqlite_master\n"
                                   "WHERE type='table'\nORDER BY name")
        self.res_tv = ttk.Treeview(query, show="headings", height=14,
                                   style=self._style_seed + ".Treeview")
        self.res_tv.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        qbb = tk.Frame(query, bg=t.get("bg", "#16161e"))
        qbb.pack(fill=tk.X)
        self._mk_btn(qbb, "Export CSV", self.export_query_csv).pack(
            side=tk.LEFT, padx=4, pady=2)
        self._mk_btn(qbb, "Copy as Markdown", self.copy_query_md).pack(
            side=tk.LEFT, padx=2, pady=2)
        self.query_status = tk.Label(
            qbb, text="", anchor="w", bg=t.get("bg", "#16161e"),
            fg=t.get("text_muted", "#8a8a9a"))
        self.query_status.pack(side=tk.LEFT, padx=8)

        # ---- Info tab
        info = tk.Frame(self.nb, bg=t.get("bg", "#16161e"))
        self.nb.add(info, text=" Info ")
        self.info_txt = tk.Text(
            info, wrap="word", relief="flat", bd=0,
            bg=t.get("editor", "#1b1b24"), fg=t.get("text", "#e8e8f0"),
            font=("TkFixedFont", 10), state=tk.DISABLED)
        self.info_txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_statusbar(self):
        t = self.theme
        self.status = tk.Label(
            self, text="ready", anchor="w",
            bg=t.get("header", "#242432"),
            fg=t.get("text_muted", "#8a8a9a"), padx=10, pady=3)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _mk_btn(self, parent, text, cmd):
        t = self.theme
        return tk.Button(
            parent, text=text, command=cmd, relief="flat", bd=0,
            bg=t.get("hover", "#2c2c3e"), fg=t.get("text", "#e8e8f0"),
            activebackground=t.get("border", "#3a3a4e"),
            activeforeground=t.get("text", "#e8e8f0"),
            padx=10, pady=2, cursor="hand2")

    # ---------------------------------------------------------- state
    def set_status(self, msg, ok=False):
        t = self.theme
        self.status.config(
            text=msg,
            fg=t.get("success", "#5ad19c") if ok else
            t.get("text_muted", "#8a8a9a"))

    def set_title_path(self):
        base = os.path.basename(self.db_path) if self.db_path else \
            "No database loaded"
        mode = "read-only" if self.read_only.get() else "read-write"
        self.title(f"SQLite Lab — {base} ({mode}) — DXN1 STUDIO")
        try:
            shown = os.path.relpath(self.db_path, self.workspace) \
                if (self.db_path and self.workspace and
                    self.db_path.startswith(self.workspace)) else self.db_path
        except ValueError:
            shown = self.db_path
        self.path_lbl.config(text=shown or base)

    def load_db(self, path):
        """Connect to *path* and populate everything."""
        try:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
            self.conn = connect(path, read_only=self.read_only.get())
            self.db_path = path
        except sqlite3.Error as exc:
            messagebox.showerror("SQLite Lab", f"Cannot open database:\n{exc}",
                                 parent=self)
            return
        self._last_result = None
        self.set_title_path()
        self.refresh()
        self.load_info()

    def pick_db(self):
        path = filedialog.askopenfilename(
            parent=self, title="Open a SQLite database",
            filetypes=[("SQLite databases", "*.db *.sqlite *.sqlite3 *.db3"),
                       ("All files", "*.*")])
        if path and os.path.isfile(path):
            self.load_db(path)

    def toggle_readonly(self):
        self.read_only.set(not self.read_only.get())
        self.rw_btn.config(
            text="read-only ✓" if self.read_only.get() else "READ-WRITE ⚠")
        if self.db_path:
            self.load_db(self.db_path)

    def refresh(self):
        """Reload the tables sidebar (keeps current tabs sane)."""
        if self.conn is None:
            return
        self.tables_tv.delete(*self.tables_tv.get_children())
        for ti in list_tables(self.conn):
            kind = ti["kind"]
            rows = "—" if ti["rows"] is None else f"{ti['rows']:,}"
            self.tables_tv.insert(
                "", "end", text=ti["name"],
                values=(kind, rows),
                tags=("view",) if kind == "view" else ())
        n = len(self.tables_tv.get_children())
        self.set_status(f"{self.db_path} — {n} table(s)/view(s)", ok=True)

    def _current_table(self):
        sel = self.tables_tv.selection()
        return self.tables_tv.item(sel[0], "text") if sel else ""

    def _on_table_select(self, _e=None):
        self.load_schema(self._current_table())

    def _on_table_open(self, _e=None):
        name = self._current_table()
        if not name:
            return
        self.nb.select(0)
        self.reload_current_table(name)

    def reload_current_table(self, name=None):
        if self.conn is None:
            return
        name = name or self._current_table()
        if not name:
            return
        try:
            limit = max(1, min(10000, int(self.limit_var.get())))
        except ValueError:
            limit = 200
        cols, rows, err = sample_rows(self.conn, name, limit=limit)
        if err:
            self.browse_status.config(text=err)
            return
        self._last_result = (cols, rows)
        self.browse_tv.delete(*self.browse_tv.get_children())
        self.browse_tv["columns"] = cols
        for c in cols:
            self.browse_tv.heading(c, text=c)
            self.browse_tv.column(c, width=min(220, max(64, 11 * len(c))),
                                  stretch=True)
        for r in rows:
            self.browse_tv.insert("", "end", values=list(r))
        self.browse_status.config(text=f"{name}: {len(rows)} row(s) shown"
                                       f" (limit {limit})")

    def load_schema(self, name):
        if self.conn is None or not name:
            return
        self.cols_tv.delete(*self.cols_tv.get_children())
        for c in table_columns(self.conn, name):
            self.cols_tv.insert("", "end", text=c["name"], values=(
                c["type"], "NO" if c["notnull"] else "yes",
                "" if c["dflt_value"] is None else str(c["dflt_value"]),
                c["pk"]))
        self.idx_tv.delete(*self.idx_tv.get_children())
        for ix in table_indexes(self.conn, name):
            flags = []
            if ix["unique"]:
                flags.append("unique")
            if ix["origin"] == "pk":
                flags.append("pk")
            self.idx_tv.insert("", "end", text=ix["name"],
                               values=(" ".join(ix["cols"]),
                                       ",".join(flags) or "—"))

    def load_info(self):
        if self.conn is None:
            return
        lines = []
        for label, value in db_info(self.conn):
            lines.append(f"{label:<16} {value}")
        lines.append("")
        lines.append("The lab opens databases read-only by default — "
                     "flip the toggle top-right for a read-write session "
                     "if you must. Every query runs as one statement; "
                     "grids cap at 500 rows.")
        self.info_txt.config(state=tk.NORMAL)
        self.info_txt.delete("1.0", "end")
        self.info_txt.insert("1.0", "\n".join(lines))
        self.info_txt.config(state=tk.DISABLED)

    # ---------------------------------------------------------- queries
    def run_current_query(self):
        if self.conn is None:
            self.set_status("Open a database first")
            return
        sql = self.sql_txt.get("1.0", "end-1c").strip()
        if not sql:
            return
        res = run_query(self.conn, sql)
        self.res_tv.delete(*self.res_tv.get_children())
        if res["kind"] == "error":
            self.query_status.config(
                text=f"error: {res['error']}",
                fg=self.theme.get("error", "#ff7a7a"))
            self.set_status("query failed — see the Query tab")
            return
        if res["kind"] == "ok":
            self._last_result = None
            self.query_status.config(
                text=f"ok — {res['affected']} row(s) affected in "
                     f"{res['elapsed_ms']:.1f} ms",
                fg=self.theme.get("success", "#5ad19c"))
            if self.db_path and not self.read_only.get():
                self.refresh()          # keep sidebar honest after writes
            self.load_info()
            return
        cols = res["columns"]
        self._last_result = (cols, res["rows"])
        self.res_tv["columns"] = cols
        for c in cols:
            self.res_tv.heading(c, text=c)
            self.res_tv.column(c, width=min(220, max(64, 11 * len(c))),
                               stretch=True)
        for r in res["rows"]:
            self.res_tv.insert("", "end", values=list(r))
        note = "" if len(res["rows"]) < QUERY_CAP else \
            f" (capped at {QUERY_CAP})"
        self.query_status.config(
            text=f"{len(res['rows'])} row(s) in {res['elapsed_ms']:.1f} ms"
                 + note, fg=self.theme.get("success", "#5ad19c"))

    # ---------------------------------------------------------- export
    def _export_common(self, columns, rows, suffix):
        if not columns:
            self.set_status("nothing to export yet — run a query or "
                            "browse a table")
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=suffix,
            initialfile=f"{os.path.basename(self.db_path or 'export')}"
                        f"{suffix}",
            filetypes=[("CSV", "*.csv")] if suffix == ".csv" else
                      [("Markdown", "*.md")])
        if not path:
            return
        if suffix == ".csv":
            export_csv(columns, rows, path)
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(markdown_table(columns, rows))
        self.set_status(f"exported {len(rows)} row(s) → {path}", ok=True)

    def export_current_csv(self):
        if not self._last_result:
            if self._current_table():
                self.reload_current_table()
        if not self._last_result:
            self.set_status("double-click a table first")
            return
        cols, rows = self._last_result
        self._export_common(cols, rows, ".csv")

    def copy_current_md(self):
        if not self._last_result:
            self.set_status("double-click a table first")
            return
        cols, rows = self._last_result
        self._copy(markdown_table(cols, rows))

    def export_query_csv(self):
        cols, rows = self._grid_to_list(self.res_tv)
        self._export_common(cols, rows, ".csv")

    def copy_query_md(self):
        cols, rows = self._grid_to_list(self.res_tv)
        if not cols:
            self.set_status("run a SELECT first")
            return
        self._copy(markdown_table(cols, rows))

    @staticmethod
    def _grid_to_list(tv):
        cols = list(tv["columns"])
        rows = [[tv.set(i, c) for c in cols] for i in tv.get_children()]
        return cols, rows

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("copied as markdown ✓", ok=True)

    def _close(self):
        try:
            if self.conn is not None:
                self.conn.close()
        except Exception:
            pass
        self.conn = None
        self.destroy()

    def _fill_picker(self, hits):
        """No db passed in: pre-select nothing, but log picks in the
        sidebar title so the user sees what was found."""
        tip = " · ".join(os.path.basename(h) for h in hits[:5])
        more = f" (+{len(hits) - 5} more)" if len(hits) > 5 else ""
        self.path_lbl.config(text=f"found: {tip}{more}")


def open_sqlitelab(parent, theme, initial="", workspace=""):
    """Public opener — palette / menu / terminal entry point."""
    win = SQLiteLab(parent, theme, db_path=initial, workspace=workspace)
    return win
