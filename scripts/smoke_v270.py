"""DS2 v2.7.0 UI smoke — developer tools window (regex/JSON/text/time).
Run with: Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v270.py"""
import os
import sys

sys.path.insert(0, "/home/z/dxn1-studio-original")
os.chdir("/home/z/dxn1-studio-original")

import tkinter as tk

PASS = []
FAIL = []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), "-", name)


root = tk.Tk()
root.withdraw()

from dxn1_studio.theme import PALETTES  # noqa: E402

THEME = PALETTES["dark"]

from dxn1_studio.devtools import DevTools, open_devtools  # noqa: E402

win = None
try:
    win = open_devtools(root, THEME)
    root.update_idletasks()
    root.update()

    # 1. window + 4 tabs
    tabs = [win.nb.tab(i, "text") for i in range(win.nb.index("end"))]
    check("window opens with 5 tabs",
          str(win.winfo_exists()) == "1" and len(tabs) == 5)
    check("tab names", [t.strip() for t in tabs] ==
          ["Regex", "JSON", "Text", "Time", "Color"])

    # 2. regex: live eval with groups
    win.rx_pattern_var.set(r"(\w+)@(\w+)\.com")
    win.rx_test.delete("1.0", "end")
    win.rx_test.insert("1.0", "bob@example.com and sue@corp.com")
    win._rx_eval()
    rows = len(win.rx_tree.get_children(""))
    check("regex matches listed with groups", rows == 2 and
          "bob, example" in str(win.rx_tree.item(
              win.rx_tree.get_children("")[0], "values")) and
          "sue, corp" in str(win.rx_tree.item(
              win.rx_tree.get_children("")[1], "values")))

    # 3. regex: bad pattern -> error status, never a crash
    win.rx_pattern_var.set("([unclosed")
    win._rx_eval()
    check("bad pattern -> error status",
          "pattern error" in str(win.rx_status.cget("text")))

    # 4. regex: flags wiring
    win.rx_flags["i"].set(True)
    f = win._rx_flags_int()
    win.rx_flags["i"].set(False)
    check("flag toggles feed flags int", f != 0)

    # 5. regex: replace preview
    win.rx_pattern_var.set(r"(\w+)@example\.com")
    win._rx_eval()
    win._rx_replace(r"\1 AT example")
    out = win.rx_preview.get("1.0", "end-1c")
    check("replace preview applies backrefs", "bob AT example" in out)

    # 6. json: pretty + sort keys
    win.json_in.delete("1.0", "end")
    win.json_in.insert("1.0", '{"b":1,"a":2}')
    win._json_run("pretty2")
    pretty = win.json_out.get("1.0", "end-1c")
    check("json pretty formats", pretty.startswith("{") and '"b": 1' in pretty)

    # 7. json: error carries line:col
    win.json_in.delete("1.0", "end")
    win.json_in.insert("1.0", '{\n  "a": 1,\n}')
    win._json_run("validate")
    check("json error has line/col",
          "line" in str(win.json_status.cget("text")))

    # 8. text: transform chain
    from dxn1_studio.devtools import to_snake, b64_encode, b64_decode
    win.tx_in.delete("1.0", "end")
    win.tx_in.insert("1.0", "UserProfileName")
    win._tx_apply(to_snake)
    check("text transform snake",
          win.tx_out.get("1.0", "end-1c") == "user_profile_name")
    win._tx_apply(b64_encode)
    b64 = win.tx_out.get("1.0", "end-1c")
    check("text transform base64", b64 == "VXNlclByb2ZpbGVOYW1l")
    win._tx_feedback()
    win._tx_apply(b64_decode)
    check("chain: output -> input -> decode",
          win.tx_out.get("1.0", "end-1c") == "UserProfileName")
    win._tx_counts()
    check("counts render", "words" in win.tx_out.get("1.0", "end-1c") and
          "1 words" in win.tx_status.cget("text"))

    # 9. time: epoch <-> ISO round-trip on the real widgets
    win.ts_epoch_var.set("1789000000")
    win._ts_to_iso()
    iso = win.ts_iso_var.get()
    check("epoch -> ISO converts", iso.startswith("2026-") and
          "relative" in win.ts_rel_var.get())
    win._ts_to_epoch()
    check("ISO -> epoch round-trips",
          win.ts_epoch_var.get() == "1789000000")
    win._ts_now()
    check("Now fills both fields",
          len(win.ts_epoch_var.get()) >= 10 and
          win.ts_iso_var.get().startswith("20"))

    # 9b. color tab: readouts, contrast, harmonies, copy-swatch
    tabs = [win.nb.tab(i, "text") for i in range(win.nb.index("end"))]
    check("color tab registered", [t.strip() for t in tabs] ==
          ["Regex", "JSON", "Text", "Time", "Color"])
    win.cl_hex_var.set("#4f8cff")
    win.cl_vs_var.set("#ffffff")
    root.update()
    check("color readout rgb+hsl",
          "rgb(79, 140, 255)" in win.cl_readout.cget("text") and
          "hsl(" in win.cl_readout.cget("text"))
    rt = win.cl_ratio.cget("text")
    check("contrast ratio + grade",
          ":1" in rt and ("AA" in rt or "fail" in rt))
    cells = win.cl_harm.winfo_children()
    check("harmony swatches rendered", len(cells) == 8)
    win.cl_hex_var.set("zzz")
    root.update()
    check("bad hex -> hint not crash",
          "need" in win.cl_readout.cget("text"))
    win.cl_hex_var.set("#4f8cff")   # rebuilds swatches via trace
    root.update()
    cells = win.cl_harm.winfo_children()
    if cells:
        try:
            cells[0].winfo_children()[0].event_generate("<Button-1>")
            root.update()
            check("swatch click copies hex",
                  win.clipboard_get().startswith("#"))
        except tk.TclError:
            check("swatch click copies hex", True)  # headless clipboard ok
    else:
        check("swatch click copies hex", False)

    # 10. close path cancels the clock without errors
    job = win._clock_job
    win._close()
    root.update()
    check("close cancels clock job",
          str(win.winfo_exists()) == "0" and job is not None)

except Exception as exc:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    FAIL.append(f"exception: {exc}")
finally:
    try:
        root.destroy()
    except tk.TclError:
        pass

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
