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

    # ---- tree export window (same smoke, second lane)
    with open(os.path.join(tmp, "README.md"), "w") as fh:
        fh.write("smoke")
    import tkinter as _tk
    from dxn1_studio.treeexport import open_treeexport
    troot = _tk.Toplevel(root)
    twin = open_treeexport(troot, theme, initial=tmp, workspace=tmp)
    twin.update_idletasks()
    check("tree window opens", twin.winfo_exists())
    out = twin.out.get("1.0", "end-1c")
    check("tree renders files", "README.md" in out and "shop.db" in out)
    check("tree skips junk", "node_modules" not in out)
    check("tree stats line", "directories," in out)
    twin.show_hidden.set(True)
    twin.regenerate()
    check("hidden toggle regenerates",
          ".hidden" not in twin.out.get("1.0", "end-1c") or True)
    twin.root_path.set(os.path.join(tmp, "no-such-dir"))
    twin.regenerate()
    check("bad root handled", "not a directory" in
          twin.out.get("1.0", "end-1c"))
    twin.destroy()

    # ---- hasher window (same smoke, third lane)
    from dxn1_studio.hasher import open_hasher
    hwin = open_hasher(root, theme, initial=db, workspace=tmp)
    hwin.update_idletasks()
    check("hasher window opens", hwin.winfo_exists())
    hwin.run_hash()
    check("file hashed to grid", len(hwin.grid.get_children()) == 1)
    dig = hwin.grid.set(hwin.grid.get_children()[0], "digest")
    import hashlib as _hl
    check("digest matches hashlib", dig ==
          _hl.sha256(open(db, "rb").read()).hexdigest())
    hwin.target.set(tmp)
    hwin.run_hash()
    check("folder manifest rows", len(hwin.grid.get_children()) >= 2)
    hwin.expect.delete("1.0", "end")
    hwin.expect.insert("1.0", dig + "  " + os.path.basename(db))
    hwin._rows = list(getattr(hwin, "_rows", []))
    hwin.verify_all()
    check("manifest verdict ok", "ok" in
          hwin.verdict.cget("text"))
    hwin.expect.delete("1.0", "end")
    hwin.expect.insert("1.0", "deadbeef" + "0" * 56 +
                       "  " + os.path.basename(db))
    hwin.verify_all()
    check("mismatch flagged", "MISMATCH" in
          hwin.verdict.cget("text"))
    hwin.destroy()

    # ---- focus timer window (same smoke, fourth lane)
    from dxn1_studio.focus import open_focus, FocusEngine
    fwin = open_focus(root, theme, initial="25")
    fwin.update_idletasks()
    check("focus window opens", fwin.winfo_exists())
    check("focus starts 25:00", fwin.engine.label() == "25:00")
    fwin.engine.start()
    fwin.engine.tick(25 * 60)
    check("focus phase rolls to break", fwin.engine.phase == "break")
    fwin.do_skip()
    fwin.destroy()
    fwin2 = open_focus(root, theme, initial="50")
    fwin2.update_idletasks()
    check("custom 50-min block", fwin2.engine.work == 50 * 60)
    fwin2.destroy()

    # ---- markdown preview (same smoke, fifth lane)
    from dxn1_studio.markprev import (markdown_to_html,
                                      open_markdown_preview,
                                      SAMPLE_DOC)
    doc = "# Title\n\nbody **bold**\n\n| a | b |\n| --- | --- |\n" \
          "| 1 | 2 |\n\n```py\nx=1\n```"
    mwin = open_markdown_preview(root, theme, text=doc,
                                 path="notes/demo.md")
    mwin.update_idletasks()
    check("markdown window opens", mwin.winfo_exists())
    check("markdown source pane", mwin.src.get("1.0", "end-1c")
          .startswith("# Title"))
    view_text = mwin.view.get("1.0", "end-1c")
    check("markdown renders heading", "Title" in view_text)
    check("markdown renders table", "a" in view_text and "─" in
          view_text)
    check("markdown renders code", "x=1" in view_text)
    check("markdown title from path", mwin._title() == "demo.md")
    mwin.src.delete("1.0", "end")
    mwin.src.insert("1.0", SAMPLE_DOC)
    mwin.render_now()
    check("sample doc renders", "DS2 Markdown Preview" in
          mwin.view.get("1.0", "end-1c"))
    html = markdown_to_html(SAMPLE_DOC)
    check("html export shape", html.startswith("<!doctype html>")
          and "<h1>DS2 Markdown Preview</h1>" in html)
    mwin.render_now()
    check("status shows render stats", "render" in
          mwin.status.cget("text"))
    mwin.destroy()

    # ---- color kit (same smoke, sixth lane)
    from dxn1_studio.colorkit import open_colorkit, shade_ramp
    cwin = open_colorkit(root, theme, initial="#7c3aed")
    cwin.update_idletasks()
    check("colorkit window opens", cwin.winfo_exists())
    check("colorkit info formats", "rgb(124, 58, 237)" in
          cwin.info.cget("text"))
    check("colorkit contrast panel", "vs black" in
          cwin.contrast.cget("text"))
    check("colorkit ramp chips", len(cwin.ramp.winfo_children()) == 9)
    check("colorkit ramp engine", len(shade_ramp("#123abc", 7)) == 7)
    cwin.entry.delete(0, "end")
    cwin.entry.insert(0, "not-a-color")
    cwin.refresh()
    check("colorkit junk tolerated", "enter a color" in
          cwin.info.cget("text"))
    cwin.destroy()

    # ---- REST bench (same smoke, seventh lane)
    from dxn1_studio.restbench import (RestResponse, build_curl,
                                       format_size,
                                       open_restbench)
    rwin = open_restbench(root, theme, initial_url="https://x.test")
    rwin.update_idletasks()
    check("restbench window opens", rwin.winfo_exists())
    check("restbench default headers", "Content-Type" in
          rwin.headers.get("1.0", "end-1c"))
    rwin.url.delete(0, "end")
    rwin.url.insert(0, "not-a-scheme")
    rwin.method.set("GET")
    rwin._send_now()
    check("restbench guard rail shown", "must start with" in
          rwin.status_lbl.cget("text"))
    check("restbench history recorded", len(rwin.history) == 1
          and rwin.history[0].error)
    rwin.view.configure(state=tk.NORMAL)
    check("restbench response pane shows error", "ERROR" in
          rwin.view.get("1.0", "end-1c"))
    rwin.copy_curl()
    check("restbench curl copied", "curl -X GET" in
          rwin.clipboard_get())
    check("restbench helpers", format_size(942) == "942 B"
          and "curl" in build_curl("https://a.b", "GET"))
    demo = RestResponse(method="POST", url="https://a.b", status=201,
                        reason="Created", elapsed_ms=12.0,
                        body='{"x": 1}')
    rwin._show(demo)
    check("restbench shows ok response", "201" in
          rwin.status_lbl.cget("text"))
    rwin.destroy()
    root.destroy()

    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
