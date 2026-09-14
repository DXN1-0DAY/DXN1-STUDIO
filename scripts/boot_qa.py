"""DS2 boot QA — boots the real studio and verifies the furniture.

Run with: DISPLAY=:99 python3 scripts/boot_qa.py

Checks (no native dialogs are opened — those block under Xvfb):
  1. every top-level menu exists and every entry has a live binding
  2. menus survive re-renders (theme switch calls setup_menu again)
  3. the workshop commands resolve (importable openers)
  4. palette contains the DS2 tool entries
Exits 0 on success, 1 with a report otherwise.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

RESULTS = []


def check(name, cond):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def main():
    import tkinter as tk

    from dxn1_studio.app import DXN1Studio
    from dxn1_studio.config import Config

    app = DXN1Studio(Config(), smoke_test=True, no_splash=True)
    root = app.root
    root.update_idletasks()
    root.update()

    # 1. menus alive + bound
    btns = [w for w in app.menu_bar.winfo_children()
            if isinstance(w, tk.Menubutton)]
    names = [b.cget("text") for b in btns]
    check("all menus present",
          set(names) >= {"File", "Edit", "View", "Tools", "Help"})
    check("Workshop menu present", "Workshop" in names)
    alive, total, unbound, entries = 0, 0, [], 0
    for w in btns:
        path = root.tk.eval(str(w) + " cget -menu")
        if root.tk.eval("winfo exists " + path) != "1":
            unbound.append((w.cget("text"), "<menu destroyed>"))
            continue
        alive += 1
        n = int(root.tk.eval(path + " index end"))
        for i in range(n + 1):
            if root.tk.eval(f"{path} type {i}") != "command":
                continue
            entries += 1
            total += 1
            cmd = root.tk.eval(f"{path} entrycget {i} -command")
            if not cmd or "deleted" in cmd.lower():
                unbound.append((w.cget("text"),
                                root.tk.eval(
                                    f"{path} entrycget {i} -label")))
            else:
                bound_ok = True
    check(f"menus alive ({alive}/{len(btns)})", alive == len(btns))
    check(f"all {entries} menu entries bound",
          total == entries and not unbound)
    for u in unbound:
        print("  UNBOUND:", u)

    # 2. re-render safety
    app.setup_menu()
    app.setup_menu()
    root.update()
    alive2 = 0
    for w in app.menu_bar.winfo_children():
        if isinstance(w, tk.Menubutton):
            path = root.tk.eval(str(w) + " cget -menu")
            alive2 += root.tk.eval("winfo exists " + path) == "1"
    check(f"menus survive re-renders ({alive2}/{len(btns)})",
          alive2 == len(btns))

    # 3. palette contains DS2 tool entries
    try:
        cmds = app.palette_commands()
    except Exception:
        cmds = []
    labels = " | ".join(str(c[0]) for c in cmds
                        if isinstance(c, (tuple, list)) and c)
    for want in ("Developer tools", "Cron explainer", "Readability",
                 "JWT decoder", ".env lint", "Data generator"):
        check(f"palette has {want}", want.lower() in labels.lower())

    # 4. every DS2 opener module imports cleanly
    for mod, opener in (("devtools", "open_devtools"),
                        ("cronexp", "open_cron"),
                        ("readability", "open_readability"),
                        ("jwt", "open_jwt"),
                        ("envcheck", "open_envlint"),
                        ("gen", "open_generator")):
        try:
            m = __import__(f"dxn1_studio.{mod}", fromlist=[opener])
            check(f"{mod}.{opener} importable",
                  callable(getattr(m, opener, None)))
        except Exception as e:  # noqa: BLE001
            check(f"{mod}.{opener} importable", False)
            print("   ", e)

    root.winfo_toplevel().destroy()

    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
