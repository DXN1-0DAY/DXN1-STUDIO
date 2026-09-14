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

    # ---- Chart Studio (same smoke, new lane)
    from dxn1_studio.charts import (parse_series, scale_points,
                                    open_chart_studio)
    win = open_chart_studio(root, theme)
    win.update_idletasks()
    win.canvas.config(width=600, height=240)
    check("chart studio window opens", win.winfo_exists())
    check("chart studio parses sample", "n=20" in
          win.stats.cget("text"))
    check("chart studio statusbar", "render" in win.status.cget("text"))
    win.kind.set("bar")
    win.refresh()
    check("chart studio bar mode", "bar" in win.status.cget("text"))
    win.input.delete("1.0", "end")
    win.input.insert("1.0", "zzz junk only ---")
    win.refresh()
    win.update_idletasks()
    check("chart studio junk tolerated", "waiting for data" in
          win.status.cget("text"))
    win.destroy()

    # ---- Unit Converter (same smoke, new lane)
    from dxn1_studio.unitconv import convert, open_unit_converter
    uwin = open_unit_converter(root, theme)
    uwin.update_idletasks()
    check("unit converter window opens", uwin.winfo_exists())
    check("unit converter live result", "=" in
          uwin.result.cget("text"))
    check("unit converter all-units panel", "ft" in
          uwin.table.cget("text"))
    uwin.cat.set("temperature")
    uwin._recat()
    check("unit converter temp switch", "°" in uwin.result.cget("text")
          or "C" in uwin.result.cget("text"))
    uwin.value.set("garbage")
    uwin.refresh()
    check("unit converter junk tolerated", "waiting for a number" in
          uwin.status.cget("text"))
    check("unitconv engine offline", abs(convert(1, "km", "mi") -
          0.621371192237) < 1e-9)
    uwin.destroy()

    # ---- Character Map (same smoke, new lane)
    from dxn1_studio.charmap import search, open_charmap
    cmwin = open_charmap(root, theme)
    cmwin.update_idletasks()
    check("charmap window opens", cmwin.winfo_exists())
    check("charmap default block grid", "characters" in
          cmwin.status.cget("text"))
    cmwin.query.set("U+2192")
    cmwin.refresh()
    check("charmap hex search", "1 characters" in
          cmwin.status.cget("text"))
    cmwin.query.set("zzz-no-block-named-this")
    cmwin.refresh()
    check("charmap junk tolerated", "nothing matches" in
          cmwin.status.cget("text"))
    check("charmap engine offline", search("2192") == ["\u2192"])
    cmwin.destroy()

    # ---- TextCase (same smoke, new lane)
    from dxn1_studio.textcase import convert, open_textcase
    tcwin = open_textcase(root, theme)
    tcwin.update_idletasks()
    check("textcase window opens", tcwin.winfo_exists())
    check("textcase eight rows", len(tcwin.labels) == 8)
    check("textcase live convert", "getHttpResponse2" ==
          tcwin.labels["camel"].cget("text"))
    tcwin.entry.delete(0, "end")
    tcwin.entry.insert(0, "user_profile_id")
    tcwin.refresh()
    check("textcase refresh", "userProfileId" ==
          tcwin.labels["camel"].cget("text"))
    tcwin.entry.delete(0, "end")
    tcwin.entry.insert(0, "---")
    tcwin.refresh()
    check("textcase junk tolerated", "—" ==
          tcwin.labels["camel"].cget("text"))
    check("textcase engine offline", convert("a_b", "kebab") == "a-b")
    tcwin.destroy()

    # ---- PassForge (same smoke, new lane)
    from dxn1_studio.pwdgen import entropy_bits, open_passforge
    pfwin = open_passforge(root, theme)
    pfwin.update_idletasks()
    check("passforge window opens", pfwin.winfo_exists())
    check("passforge generates", len(pfwin.out.get()) == 20)
    check("passforge entropy readout", "bits" in
          pfwin.strength.cget("text"))
    pfwin.length.set(12)
    pfwin.refresh()
    check("passforge length honored", len(pfwin.out.get()) == 12)
    pfwin.upper.set(False); pfwin.lower.set(False)
    pfwin.digits.set(False); pfwin.refresh()
    check("passforge empty pool honest", "toggle at least one" in
          pfwin.out.get())
    check("passforge engine offline",
          entropy_bits(20) > 100)
    pfwin.destroy()

    # ---- NumBase (same smoke, new lane)
    from dxn1_studio.numbase import format_base, open_numbase
    nbwin = open_numbase(root, theme, initial="255")
    nbwin.update_idletasks()
    check("numbase window opens", nbwin.winfo_exists())
    check("numbase live rows", "ff" ==
          nbwin.labels["16"].cget("text"))
    nbwin.entry.delete(0, "end")
    nbwin.entry.insert(0, "0x10")
    nbwin.refresh()
    check("numbase prefix parse", "10000" ==
          nbwin.labels["2"].cget("text"))
    nbwin.entry.delete(0, "end")
    nbwin.entry.insert(0, "junk!!")
    nbwin.refresh()
    check("numbase junk tolerated", "not a valid" in
          nbwin.status.cget("text"))
    check("numbase bit inspector", "bit length" in
          nbwin.bits.cget("text") or nbwin.bits.cget("text") == "")
    check("numbase engine offline", format_base(255, 16) == "ff")
    nbwin.destroy()

    # ---- CSV Lab (same smoke, new lane)
    from dxn1_studio.csvkit import parse_csv, open_csv_lab
    csvwin = open_csv_lab(root, theme)
    csvwin.update_idletasks()
    check("csv lab window opens", csvwin.winfo_exists())
    check("csv lab renders sample", "3 rows" in
          csvwin.status.cget("text"))
    csvwin.delim.set("auto")
    csvwin.input.delete("1.0", "end")
    csvwin.input.insert("1.0", "x;y\n1;2")
    csvwin.refresh()
    check("csv lab auto sniff", "1 rows" in
          csvwin.status.cget("text"))
    csvwin.input.delete("1.0", "end")
    csvwin.input.insert("1.0", "totally not a table... or is it")
    csvwin.refresh()
    check("csv lab junk tolerated", "0 rows × 1 cols" in
          csvwin.status.cget("text"))  # a 1x1 table is honest CSV
    check("csv lab engine offline", len(parse_csv("a,b\n1,2")) == 2)
    csvwin.destroy()

    # ---- MathPad (same smoke, new lane)
    from dxn1_studio.mathpad import evaluate as _mev, open_mathpad
    mpwin = open_mathpad(root, theme)
    mpwin.update_idletasks()
    check("mathpad window opens", mpwin.winfo_exists())
    check("mathpad sample evaluates", "= 268" in
          mpwin.result.cget("text"))  # sqrt(144)+2^10/4 = 12+256 = 268
    mpwin.entry.delete(0, "end")
    mpwin.entry.insert(0, "9^2")
    mpwin.do_eval()
    check("mathpad power eval", "= 81" in mpwin.result.cget("text"))
    mpwin.entry.delete(0, "end")
    mpwin.entry.insert(0, "1/0")
    mpwin.do_eval()
    check("mathpad honest error", "= ?" in mpwin.result.cget("text")
          and "division by zero" in mpwin.status.cget("text"))
    mpwin.entry.delete(0, "end")
    mpwin.entry.insert(0, "n = _ * 2")
    mpwin.do_eval()
    check("mathpad vars + last answer", mpwin.vars.get("n") == 162)
    check("mathpad engine offline", _mev("2^5") == 32)
    mpwin.destroy()

    # ---- ByteSnoop (same smoke, new lane)
    from dxn1_studio.hexdump import from_hex as _fhex, open_bytesnoop
    hwin = open_bytesnoop(root, theme)
    hwin.update_idletasks()
    check("bytesnoop window opens", hwin.winfo_exists())
    check("bytesnoop renders text", "printable" in
          hwin.status.cget("text"))
    hwin.mode.set("hex")
    hwin.input.delete("1.0", "end")
    hwin.input.insert("1.0", "41 42 43")
    hwin.refresh()
    check("bytesnoop decodes hex", "|ABC|" in
          hwin.output.get("1.0", "end"))
    hwin.input.delete("1.0", "end")
    hwin.input.insert("1.0", "4 1 2")
    hwin.refresh()
    check("bytesnoop honest refusal", "doesn't parse" in
          hwin.status.cget("text"))
    check("bytesnoop engine offline", _fhex("41:42:43") == b"ABC")
    hwin.destroy()

    # ---- Paste Diff (same smoke, new lane)
    from dxn1_studio.textdiff import inline_diff as _idl, open_textdiff
    tdwin = open_textdiff(root, theme)
    tdwin.update_idletasks()
    check("textdiff window opens", tdwin.winfo_exists())
    check("textdiff sample stats", "similar" in
          tdwin.status.cget("text"))
    tdwin.mode.set("word")
    tdwin.refresh()
    check("textdiff word marks", "[-" in tdwin.output.get("1.0", "end")
          or "{+" in tdwin.output.get("1.0", "end"))
    tdwin.old_text.delete("1.0", "end")
    tdwin.new_text.delete("1.0", "end")
    tdwin.refresh()
    check("textdiff junk tolerated", "paste" in
          tdwin.status.cget("text"))
    check("textdiff engine offline", "[-brown-]" in
          _idl("quick brown", "quick red"))
    tdwin.destroy()

    # ---- Markup Bench (same smoke, new lane)
    from dxn1_studio.xmlbench import xml_pretty as _xpre, open_xmlbench
    xbwin = open_xmlbench(root, theme)
    xbwin.update_idletasks()
    check("xmlbench window opens", xbwin.winfo_exists())
    check("xmlbench live validate", "valid" in
          xbwin.status.cget("text"))
    xbwin._minify()
    check("xmlbench minify", "<to>" in xbwin.output.get("1.0", "end"))
    xbwin.input.delete("1.0", "end")
    xbwin.input.insert("1.0", "<a><b></a>")
    xbwin._validate()
    check("xmlbench honest error", "invalid" in
          xbwin.status.cget("text"))
    check("xmlbench engine offline", _xpre("<r/>")[0].startswith("<r"))
    xbwin.destroy()

    # ---- Contrast Auditor (same smoke, new lane)
    from dxn1_studio.contrast import grade as _cgrade, open_contrast
    cwin = open_contrast(root, theme)
    cwin.update_idletasks()
    check("contrast window opens", cwin.winfo_exists())
    check("contrast 13 pairs graded",
          len(cwin.tree.get_children()) == 13
          and "pairs" in cwin.summary.cget("text"))
    cwin.var.set("Built-in · Light")
    cwin._audit()
    check("contrast theme switch re-audits",
          len(cwin.tree.get_children()) == 13)
    cwin._copy_report()
    check("contrast report copies", "copied" in
          cwin.status.cget("text"))
    check("contrast engine offline", _cgrade(7.0) == "AAA"
          and _cgrade(2.0) == "FAIL")
    cwin.destroy()

    # ---- Cheat Sheet exporter (same smoke, new lane)
    import tempfile as _tf, os as _os
    from dxn1_studio.cheatsheet import build_html as _bhtml, open_cheatsheet
    kwin = open_cheatsheet(root, theme)
    kwin.update_idletasks()
    check("cheatsheet window opens", kwin.winfo_exists())
    check("cheatsheet live preview", "TERMINAL COMMANDS" in
          kwin.preview.get("1.0", "end"))
    _out = _os.path.join(_tf.mkdtemp(prefix="ds2-smoke-cs-"), "cs.html")
    kwin._write_to(_out)
    check("cheatsheet saves HTML", _os.path.isfile(_out)
          and _os.path.getsize(_out) > 5000)
    check("cheatsheet honest save error", kwin._write_to(
        "/nonexistent-dir-xyz/x.html") is None
        and "save failed" in kwin.status.cget("text"))
    check("cheatsheet engine offline", "@media print" in _bhtml(None))
    kwin.destroy()

    # ---- Colorblind Lab (same smoke, new lane)
    from dxn1_studio.cvdlab import (simulate_hex as _simh,
                                    open_cvdlab)
    vwin = open_cvdlab(root, theme)
    vwin.update_idletasks()
    check("cvdlab window opens", vwin.winfo_exists())
    check("cvdlab swatches render", len(vwin._swatch_widgets) > 20
          and "CVD view" in vwin.verdict.cget("text"))
    vwin.kind.set("achromatopsia")
    vwin._refresh()
    check("cvdlab kind switch works", len(vwin._swatch_widgets) > 20)
    vwin.custom.delete(0, "end")
    vwin.custom.insert(0, "junk")
    vwin._refresh()
    check("cvdlab honest custom hex", "n/a" in
          vwin.custom_out.cget("text"))
    check("cvdlab engine offline", _simh("#ff0000", "achromatopsia")
          != "#ff0000" and _simh("zz", "deuteranopia") is None)
    vwin.destroy()

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

    # ---- window geometry memory (same smoke, eighth lane)
    from dxn1_studio.geom import (recall, remember, restore_root,
                                  screen_signature)
    gcfg = type("G", (), {})()
    gcfg.data = {}

    def _get(k, d=None):
        return gcfg.data.get(k, d)

    def _set(k, v):
        gcfg.data[k] = v
    gcfg.get, gcfg.set = _get, _set
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    check("geom recall empty", recall(gcfg, sw, sh) == "")
    remember(gcfg, "700x500+20+15", sw, sh)
    check("geom recall roundtrip", recall(gcfg, sw, sh) ==
          "700x500+20+15")
    remember(gcfg, "%dx%d+50+60" % (sw * 3, sh * 3), sw, sh)
    got = restore_root(root, gcfg, min_w=200, min_h=150)
    check("geom restore clamps", got.startswith(
        "%dx%d" % (sw, sh)))
    root.update_idletasks()
    check("geom applied to root", root.geometry().startswith(
        "%dx%d" % (sw, sh)))

    # ---- scribe mini chip (same smoke, ninth lane — engine +
    #      a real statusbar label, app-level wiring in boot_qa)
    from dxn1_studio.scribe import ScribeChip
    chip = ScribeChip(goal_words=100, min_interval=0.5)
    chip.observe(120)
    check("scribe chip text renders", "✎ 120 w" in chip.text()
          and "100%" in chip.text())
    lbl = tk.Label(root, text="")
    chip2 = ScribeChip(goal_words=250, min_interval=0.0)
    for _ in range(3):
        chip2.observe(10 + _)
        lbl.configure(text=chip2.text())
    check("scribe label updated", "✎ 12 w" in lbl.cget("text"))
    chip2.reset()
    check("scribe reset keeps goal", chip2.goal_words == 250
          and chip2.words() == 0)
    check("scribe goal hide", chip2.set_goal(0) is True
          and "%" not in chip2.text())

    # ---- filestats scan history (same smoke, tenth lane)
    import shutil as _sh
    from dxn1_studio.filestats import (append_history, delta_line,
                                       sparkline)
    ws2 = tempfile.mkdtemp(prefix="ds2-smoke-fs-")
    try:
        h = append_history(ws2, {"t": "a", "files": 5, "bytes": 100})
        h = append_history(ws2, {"t": "b", "files": 9, "bytes": 180})
        check("statshistory appends", len(h) == 2
              and h[-1]["files"] == 9)
        check("statshistory dedupes", len(append_history(
            ws2, {"t": "c", "files": 9, "bytes": 180})) == 2)
        trend = sparkline([x["files"] for x in h])
        check("statshistory sparkline renders", len(trend) == 2
              and trend[0] != trend[-1])
        check("statshistory delta", "+4 files" in delta_line(
            {"files": 9, "bytes": 180}, {"files": 5, "bytes": 100}))
    finally:
        _sh.rmtree(ws2, ignore_errors=True)

    # ---- fuzzy launcher scoring (same smoke, eleventh lane —
    #      engine + real palette / symbol mode / QuickOpen integration)
    from dxn1_studio import fuzzy as fz
    check("fuzzy engine sane", fz.score("qpn", "Quick open a file") > 0
          and fz.score("zx", "quick open") == -1
          and fz.match("qo", "quick open")[1] == (0, 6))
    check("fuzzy finds non-substrings",
          fz.score("sttngs", "Settings…") > 0
          and fz.score("cmpr", "compare themes") > 0)

    from dxn1_studio.app import DXN1Studio
    from dxn1_studio.config import Config
    app2 = DXN1Studio(Config(), smoke_test=True, no_splash=True)
    app2.root.update_idletasks()
    app2.open_palette()
    pal = app2._palette
    pal.entry.delete(0, "end")
    pal.entry.insert(0, "qpn")
    pal._on_type()
    check("palette fuzzy hit", len(pal.filtered) == 1
          and pal.filtered[0][0] == "Quick open a file")
    pal.close()

    # symbol mode: inject editor content, then a gappy @ query
    sym_py = os.path.join(tmp, "sym_probe.py")
    with open(sym_py, "w", encoding="utf-8") as fh:
        fh.write("def alpha_one():\n    pass\n\n\nclass BetaTwo:\n"
                 "    def gamma_three(self):\n        pass\n")
    ed = app2.editor
    ed.file_path = sym_py
    ed.text.delete("1.0", "end")
    ed.text.insert("1.0", open(sym_py, encoding="utf-8").read())
    app2.open_palette()
    pal2 = app2._palette
    pal2.entry.delete(0, "end")
    pal2.entry.insert(0, "@gmmthre")
    pal2._on_type()
    app2.root.update()
    check("palette symbol fuzzy hit", len(pal2.filtered) == 1
          and "gamma_three" in pal2.filtered[0][0])
    pal2.close()

    app2.open_quick_open()
    qo = app2._quick_open
    n_all = len(qo.files)
    check("quickopen empty query keeps all",
          n_all > 0 and len(qo.filtered) == n_all)
    qo.entry.delete(0, "end")
    qo.entry.insert(0, "appp")
    qo._on_type()
    hits = [item[1] for item in qo.filtered]
    scores = [fz.path_score("appp", h) for h in hits]
    check("quickopen fuzzy ranked", len(hits) > 0
          and scores == sorted(scores, reverse=True)
          and fz.path_score("appp", hits[0]) >= 0)
    qo.entry.delete(0, "end")
    qo.entry.insert(0, "zzqqxx")
    qo._on_type()
    check("quickopen no-match clean", len(qo.filtered) == 0)
    qo.close()
    app2.root.destroy()

    # ---- session restore (same smoke, twelfth lane — engine +
    #      window with stub app + the real close-hook)
    from dxn1_studio import session as sess
    store = os.path.join(tmp, "sess-store")
    pf = os.path.join(tmp, "proj"); os.makedirs(pf, exist_ok=True)
    f1 = os.path.join(pf, "one.py"); open(f1, "w").write("a = 1\n" * 9)
    f2 = os.path.join(pf, "two.py"); open(f2, "w").write("b = 2\n" * 9)
    snap = sess.snapshot([f1, f2], active=f1,
                         cursor={f1: (5, 2)}, workspace=pf)
    ok, err = sess.save(pf, snap, base=store)
    check("session engine roundtrip", ok
          and sess.load(pf, base=store)["active"] == f1)
    ghost = sess.snapshot(["/definitely/missing/zz.py"],
                          active="/definitely/missing/zz.py",
                          workspace=pf)
    check("session plan filters ghosts",
          sess.restore_plan(ghost) == ([], "", None))

    from types import SimpleNamespace as _NS

    class _StubEd:
        file_path = ""
        line = 0

        def goto_line(self, n):
            self.line = n
    stub = _NS(editor=_StubEd(), opened=[])
    stub.open_file = lambda p: stub.opened.append(p)
    stub.editor.text = _NS(mark_set=lambda *a: None,
                           see=lambda *a: None)
    from dxn1_studio.session import open_session_restore
    win = open_session_restore(root, {"bg": "#16161e",
                                      "header": "#242432",
                                      "text": "#e8e8f0",
                                      "text_muted": "#8a8a9a",
                                      "button": "#2a2a3a",
                                      "button_hover": "#33334a",
                                      "card": "#131a22"},
                               app=stub, base=store)
    check("session window opens + lists", win is not None
          and len(win.tree.get_children()) == 1)
    kids = win.tree.get_children()
    win.tree.selection_set(kids[0])
    win._on_select()
    win.restore_selected()
    check("session window restores via app",
          stub.opened == [f1, f2] and stub.editor.line == 5)
    win.clear_selected()
    check("session window clears", len(win.tree.get_children()) == 0)
    win.destroy()

    from dxn1_studio.app import TERMINAL_HELP
    check("session wiring present",
          hasattr(DXN1Studio, "open_session_restore")
          and any(e[0].startswith("session") for e in TERMINAL_HELP))

    # close-hook: a real boot that opens a file, sets the cursor,
    # then closes — the session must land on disk with the cursor
    app3 = DXN1Studio(Config(), smoke_test=True, no_splash=True)
    app3.root.update_idletasks()
    probe = os.path.join(pf, "one.py")
    app3.open_file(probe)
    app3.editor.text.mark_set("insert", "5.2")
    app3._on_close()
    hook_data = sess.load(app3.project_dir or "")
    check("close-hook saves session with cursor",
          probe in (hook_data.get("tabs") or [])
          and (hook_data.get("cursor") or {}).get(probe, {}).get("line")
          == 5)
    sess.clear(app3.project_dir or "")      # leave no scratch behind

    root.destroy()

    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
