"""DS2 v2.8.0 UI smoke — cron explainer + readability report windows.
Run with: Xvfb :99 & ; DISPLAY=:99 python3 scripts/smoke_v280.py"""
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

try:
    # ------------------------------------------------------------- cron
    from dxn1_studio.cronexp import open_cron

    cron = open_cron(root, THEME, initial="*/15 9-17 * * mon-fri")
    root.update_idletasks()
    root.update()

    check("cron window opens", str(cron.winfo_exists()) == "1")
    check("cron sentence decoded",
          cron.sentence.cget("text").startswith("at minute"))
    check("cron field table has 5 rows",
          len(cron.table.get_children("")) == 5)
    runs_txt = cron.runs.get("1.0", "end-1c")
    check("cron next runs listed", runs_txt.count(":") >= 5)

    # live update on a bad expression
    cron.var.set("99 * * * *")
    root.update()
    check("cron error surfaces",
          "bad minute" in cron.error.cget("text") and
          cron.runs.get("1.0", "end-1c").strip() == "—")

    # @daily shorthand + friendly sentence
    cron.var.set("@daily")
    root.update()
    check("cron @daily decodes",
          cron.sentence.cget("text") == "at 00:00" and
          len(cron.table.get_children("")) == 5)

    # empty input = error, no crash
    cron.var.set("")
    root.update()
    check("cron empty -> error", cron.error.cget("text") != "")
    cron.destroy()
    root.update()

    # ------------------------------------------------------ readability
    from dxn1_studio.readability import open_readability

    sample = ("The cat sat on the mat. It was a cat and the cat was "
              "happy. Documentation should be clear, simple and kind to "
              "every reader who arrives tired, confused, or in a hurry "
              "with a production incident ticking away in the "
              "background.")
    read = open_readability(root, THEME, text=sample, name="README.md")
    root.update_idletasks()
    root.update()

    check("readability window opens", str(read.winfo_exists()) == "1")
    check("readability verdict shown",
          "Flesch" in read.winfo_children()[0].winfo_children()[0]
          .cget("text"))
    check("readability 8 stat cards",
          len(read.winfo_children()[1].winfo_children()) == 8)
    check("readability long sentences listed",
          len(read.long_tree.get_children("")) == 1)
    check("readability word pressure: cat x3",
          read.word_tree.item(read.word_tree.get_children("")[0],
                              "values")[0] == "cat" and
          read.word_tree.item(read.word_tree.get_children("")[0],
                              "values")[1] == "3")

    # copy report writes markdown to clipboard
    read._copy()
    root.update()
    try:
        clip = root.clipboard_get()
    except tk.TclError:
        clip = ""
    check("copy report to clipboard",
          clip.startswith("# Readability — README.md"))

    # empty file -> friendly no-prose card, no crash
    empty = open_readability(root, THEME, text="", name="empty.py")
    root.update()
    check("readability empty input safe",
          str(empty.winfo_exists()) == "1" and
          "No prose" in empty.winfo_children()[0].winfo_children()[0]
          .cget("text"))
    empty.destroy()
    read.destroy()
    root.update()

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
