"""UI smoke for the SQLite Lab (v2.9.0) — boots the real window under Xvfb.

Checks: window + tabs exist, table sidebar populated, browse grid fills,
schema tab loads, query bench runs a SELECT and shows rows, error path
lands in the status label, export helpers no-op safely. Never saves
files, never touches user data (scratch DB in /tmp).
"""
import os
import sqlite3
import sys
import tempfile
import tkinter as tk

sys.path.insert(0, "/home/z/dxn1-studio-original")
from dxn1_studio import sqlitelab as sl  # noqa: E402
from dxn1_studio.config import DEFAULTS  # noqa: E402
from dxn1_studio.theme import from_config  # noqa: E402

CHECKS = []


def check(name, cond):
    CHECKS.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name)


def main():
    tmp = tempfile.mkdtemp(prefix="ds2-smoke-")
    db = os.path.join(tmp, "shop.db")
    raw = sqlite3.connect(db)
    raw.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, "
                "price REAL)")
    raw.execute("INSERT INTO items (name, price) VALUES ('bolt', 0.25), "
                "('nut', 0.10), ('beam', 3.50)")
    raw.execute("CREATE INDEX idx_name ON items (name)")
    raw.commit()
    raw.close()

    root = tk.Tk()
    root.withdraw()
    theme = from_config(DEFAULTS)
    win = sl.open_sqlitelab(root, theme, initial=db, workspace=tmp)

    check("window opens with db title", "shop.db" in win.title())
    win.update_idletasks()

    kids = win.tables_tv.get_children()
    check("sidebar lists the table", len(kids) == 1)
    check("sidebar shows row count", "3" in str(win.tables_tv.item(
        kids[0], "values")))

    win.reload_current_table("items")
    check("browse grid filled", len(win.browse_tv.get_children()) == 3)
    check("browse columns named", list(win.browse_tv["columns"]) ==
          ["id", "name", "price"])

    win.load_schema("items")
    check("schema columns loaded", len(win.cols_tv.get_children()) == 3)
    check("index listed", len(win.idx_tv.get_children()) == 1)

    win.run_current_query()   # default seeded SQL: sqlite_master SELECT
    qrows = win.res_tv.get_children()
    check("query bench returns rows", len(qrows) >= 1)
    check("query status ok", "row(s)" in win.query_status.cget("text"))

    win.sql_txt.delete("1.0", "end")
    win.sql_txt.insert("1.0", "SELEC broken")
    win.run_current_query()
    check("syntax error surfaces in status",
          "error" in win.query_status.cget("text"))

    win.sql_txt.delete("1.0", "end")
    win.sql_txt.insert("1.0", f"SELECT name FROM items WHERE price > 0.2")
    win.run_current_query()
    check("filtered query rows", len(win.res_tv.get_children()) == 2)   # bolt 0.25 + beam 3.50
    check("result captured for export", win._last_result is not None)

    win._last_result = None
    win.copy_current_md()     # no result -> status hint, no crash
    check("copy-without-result safe", "double-click" in
          win.status.cget("text"))

    win._copy("markdown test")
    check("clipboard copy works", "markdown" in
          win.clipboard_get())

    win._close()
    check("clean close", not win.winfo_exists())
    root.destroy()

    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
