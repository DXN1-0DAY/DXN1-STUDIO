#!/usr/bin/env python3
"""DS3 probe: the studio's UE5 face is real and in sync — ui/index.html
carries every panel (menubar, Place Actors, Outliner, Details, Content
Browser, Output Log, status bar, PIE bar), lists every scene on the wire
(scenes/*.dxn1.json — the SCENES array and the directory agree), wears
every image it references (assets/*.png, PNG magic verified), pins its
embedded VERSION to the repo's VERSION file (the fifth corner of the
version sync), and ships with no TODO lint. R46 adds the translate-gizmo
law and the panel laws (context menu, World Settings, content search,
PIE ride-by-stand + scene gravity). Pure-python pins, no engine."""
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(REPO, "ui", "index.html")

pins = []
t0 = time.time()


def pin(name, ok, detail=""):
    pins.append((name, bool(ok)))
    print(f"  {'ok ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail and not ok else ""))


html = ""
try:
    html = open(UI, encoding="utf-8").read()
except OSError as e:
    print(f"  FAIL cannot read {UI}: {e}")
    html = ""

# pin 1 — the editor exists and is a real body of work, not a stub
pin("ui/index.html exists and is substantial", len(html) > 20000, f"{len(html)} bytes")

# pin 2 — every UE5 panel the research doc promised is in the cloth
PANELS = [
    ("menubar", 'id="menubar"'),
    ("toolbar", 'id="toolbar"'),
    ("Place Actors", "Place Actors"),
    ("Outliner", "Outliner"),
    ("Details", "Details"),
    ("Content Browser", "Content Browser"),
    ("Output Log", "Output Log"),
    ("status bar", 'id="statusbar"'),
    ("PIE bar", 'id="piebar"'),
    ("viewport canvas", 'id="viewport"'),
]
missing = [nm for nm, marker in PANELS if marker not in html]
pin("all 10 editor panels present", not missing, ", ".join(missing))

# pin 3 — the SCENES array and the scenes/ directory agree (the sync law)
scenes_dir = sorted(f for f in os.listdir(os.path.join(REPO, "scenes"))
                    if f.endswith(".dxn1.json"))
listed = sorted(set(re.findall(r'f:"([\w.-]+\.dxn1\.json)"', html)))
pin("every scene on disk is in the editor's SCENES array",
    set(scenes_dir) <= set(listed),
    f"missing from UI: {sorted(set(scenes_dir)-set(listed))}")
pin("the editor lists no ghost scenes",
    set(listed) <= set(scenes_dir),
    f"ghosts: {sorted(set(listed)-set(scenes_dir))}")

# pin 4 — every referenced image exists and starts with the PNG magic
assets = sorted(set(re.findall(r'assets/([\w.-]+\.png)', html)))
bad = []
for a in assets:
    p = os.path.join(REPO, "ui", "assets", a)
    try:
        with open(p, "rb") as fh:
            head = fh.read(8)
        if not head.startswith(b"\x89PNG\r\n\x1a\n"):
            bad.append(f"{a}: not a PNG")
    except OSError:
        bad.append(f"{a}: missing")
pin(f"all {len(assets)} referenced ui assets are real PNGs", not bad and bool(assets),
    "; ".join(bad))

# pin 5 — the embedded VERSION equals the VERSION file (the fifth corner)
m = re.search(r'const VERSION = "([\d.]+)"', html)
ver_file = open(os.path.join(REPO, "VERSION"), encoding="utf-8").read().strip()
pin("editor VERSION pin equals the VERSION file",
    bool(m) and m.group(1) == ver_file,
    f"ui says {m.group(1) if m else '???'}, VERSION says {ver_file}")

# pin 6 — spark's constants are spoken honestly in the PIE sim
pin("PIE speaks spark's physics constants",
    "GRAV = 1500" in html and "JUMP_VY = -620" in html)

# pin 7 — no unfinished-work lint
lint = [w for w in ("TODO", "FIXME", "XXX", "placeholder-here") if w in html]
pin("no TODO/FIXME lint in the editor", not lint, ", ".join(lint))

# pin 8 — the interaction law: drag-drop placement, rubber-band select,
# multi-edit align/distribute, and localStorage desk persistence all exist
INTERACTIONS = [
    ("drag-drop placement", 'draggable="true"' in html
        and 'addEventListener("drop"' in html and "dxn1-actor" in html),
    ("rubber-band select", "mouse.marquee" in html and "band caught" in html),
    ("multi-edit align+distribute", "Center X" in html and "Distr X" in html
        and "Distr Y" in html),
    ("desk persistence", "localStorage" in html and "dxn1-studio-3-prefs" in html
        and "reset-layout" in html),
]
missing = [nm for nm, ok in INTERACTIONS if not ok]
pin("all 4 interaction laws present", not missing, ", ".join(missing))

# pin 9 — the live-boot law: the script tail renders before the wire
# answers, so renderStats must guard the empty stage or the whole
# editor dies at top level and boot() never runs (v3.1.119 shipped
# exactly this — parse-clean but never live-booted; caught by R45's
# browser smoke test). Static pin: the guard must precede ents().
mstats = re.search(r"function renderStats\(\)\{(.*?)\n\}", html, re.S)
body = mstats.group(1) if mstats else ""
guard_ok = "if(!dcur) return;" in body or "if(!S.scenes[S.cur]) return;" in body
pin("live-boot law — renderStats guards the empty stage",
    bool(mstats) and guard_ok and body.index("return;") < body.find("ents()"),
    "no empty-stage guard before ents()" if mstats and not guard_ok else "renderStats missing")

# pin 10 — the translate gizmo is real: arrows drawn at the selection's
# center and draggable along ONE axis (R46; R47 widened the anchor to
# any selection size — single = entity center, multi = bbox center).
GIZMO = ["function gizmoAnchor(", "function drawGizmo(", "function gizmoHit(",
         "mouse.gizmoAxis", "if(S.sel.size>=1&&!S.sim) drawGizmo();"]
miss = [g for g in GIZMO if g not in html]
pin("translate gizmo draws at the selection and drags by axis", not miss,
    ", ".join(miss))

# pin 11 — the R46 panel laws: outliner context menu, World Settings
# with a REAL gravity field (spark reads scene.gravity at spark.cpp:37,
# clamped ±5000 at :176), content-browser search, PIE speaking the
# ENGINE's collision law verbatim (spark never reads the solid field:
# tagless bodies are solid, movers are solid vertically only, and the
# carry is stepMovers' swept band — feet in [prevTop-2, curBottom+2]
# with horizontal overlap; level-11 has three lifts and the old PIE
# summed every mover's delta, dragging the player with all of them),
# PIE honoring the scene's own gravity, and PIE movement keys not
# leaking into the editor's tool shortcuts.
R46 = [
    ("outliner context menu",
        'addEventListener("contextmenu"' in html and 'id="ctxmenu"' in html
        and "function openCtx(" in html),
    ("world settings edits the scene's real fields",
        "World Settings" in html and 'textField("next scene"' in html
        and 'numField("gravity"' in html),
    ("content browser search filters cards",
        'id="cb-search"' in html
        and '$("cb-search").addEventListener("input",buildContent)' in html),
    ("PIE carry is the engine's swept band",
        "feet>=py0-2" in html and "swept band" in html
        and "spark.cpp stepMovers" in html),
    ("PIE solid is the engine's tag law, not the JSON's",
        "if(tagOf(e)) continue;" in html and 'tg!=="mover"' in html
        and "never reads the solid field" in html),
    ("PIE honors the scene's own gravity",
        "grav:clamp(Math.round(d.gravity||GRAV),-5000,5000)" in html
        and "p.vy+=m.grav*dt" in html),
    ("PIE movement keys do not leak into editor tools",
        'if(S.sim&&["a","d","w"' in html),
]
missing = [nm for nm, ok in R46 if not ok]
pin("all 7 R46 panel laws present", not missing, ", ".join(missing))

# pin 12 — the R47 laws: viewport tabs (multi-scene open with close
# buttons and middle-click), the multi-selection gizmo (bbox-center
# pivot, any selection size), the content-browser context menu
# (load / duplicate / rename a scene), the generated palette icon set
# (one icon per actor card), and the About modal's hero banner.
icon_refs = re.findall(r'assets/(icon-[\w-]+\.png)', html)
R47 = [
    ("viewport tabs (open/close/middle-click)",
        'id="tabbar"' in html and "function renderTabs(" in html
        and "function closeTab(" in html and "auxclick" in html),
    ("gizmo anchors any selection (bbox pivot)",
        "if(S.sel.size>=1&&!S.sim) drawGizmo();" in html
        and "the bbox center" in html),
    ("content browser context menu",
        "function openCardCtx(" in html and "Duplicate scene" in html),
    ("the palette wears its 10 generated icons",
        len(set(icon_refs)) == 10 and "assets/icon-block.png" in html
        and "assets/icon-player.png" in html),
    ("the About modal wears its hero banner",
        "assets/about-hero.png" in html),
]
missing = [nm for nm, ok in R47 if not ok]
pin("all 5 R47 studio laws present", not missing, ", ".join(missing))

# pin 13 — THE PARSE LAW (R48, earned the hard way): v3.1.119 shipped a
# syntax error inside the editor's script (`for(const x,hy] of` — a
# destructuring '[' lost to a bad merge) and FOUR releases + six gate
# runs never saw it, because every pin read strings and none parsed the
# cloth: the whole editor was dead in every browser while the gates
# stayed green. The runtime law: the script must PARSE — new Function()
# compiles it without running.
import subprocess, tempfile
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
main_script = max(scripts, key=len) if scripts else ""
parse_ok, parse_msg = False, "no <script> block found"
if main_script:
    tfd2, tfname = tempfile.mkstemp(suffix=".js")
    with os.fdopen(tfd2, "w") as tf:
        tf.write(main_script)
    try:
        r = subprocess.run(
            ["bun", "-e",
             'const src=require("fs").readFileSync(process.argv[1],"utf8");'
             'try{ new Function(src); console.log("PARSE-OK"); }'
             'catch(e){ console.log("PARSE-FAIL: "+e.message); process.exit(1); }',
             tfname],
            capture_output=True, text=True, timeout=30)
        parse_ok = r.returncode == 0 and "PARSE-OK" in r.stdout
        parse_msg = (r.stdout + r.stderr).strip()[:140]
    except Exception as e:
        parse_msg = f"runner unavailable: {e}"
    finally:
        try: os.unlink(tfname)
        except OSError: pass
pin("the editor's script PARSES (the cloth is not the runtime)",
    parse_ok, parse_msg)

# pin 14 — the R48 laws: the scale gizmo (the 8 corner squares finally
# bite: one source of truth draws and hit-tests them, anchored-edge
# scaling with an honest 8px floor, a history entry of its own), the
# open tabs persist across reloads, and the per-biome generated skies
# follow the scene (four real PNG backdrops — the JPEG-bytes law
# checked their magic).
assets_dir = os.path.join(REPO, "ui", "assets")
skies = [f for f in ("sky-twilight.png", "sky-industrial.png",
                     "sky-dawn.png", "sky-void.png")
         if os.path.isfile(os.path.join(assets_dir, f))]
magic = b""
if skies:
    with open(os.path.join(assets_dir, skies[0]), "rb") as fh:
        magic = fh.read(4)
R48 = [
    ("scale gizmo — the 8 handles bite (one truth draws and hits)",
        "function handlePos(" in html and "function scaleHit(" in html
        and "mouse.scale={ax:sh.ax" in html
        and 'pushHistory("scale ' in html),
    ("anchored-edge group scaling with the 8px floor",
        "R=Math.max(m.L0+8,sn(wx))" in html
        and "it.e.x=L+it.dx0*fx; it.e.w=Math.max(8,it.w0*fx);" in html
        and "function selBox(" in html and "function bboxHandles(" in html),
    ("open tabs persist across reloads",
        "tabs:S.openTabs," in html and "p.tabs" in html
        and "S.openTabs=t;" in html),
    ("per-biome generated skies follow the scene",
        "const SKYS={" in html and "function skyFor(" in html
        and len(skies) == 4 and magic == b"\x89PNG"),
    ("the splash wears the v2 art and the browser wears the campaign map",
        "assets/splash-v2.png" in html and 'id="cb-map"' in html
        and os.path.isfile(os.path.join(assets_dir, "splash-v2.png"))
        and os.path.isfile(os.path.join(assets_dir, "campaign-map.png"))),
]
missing = [nm for nm, ok in R48 if not ok]
pin("all 4 R48 studio laws present", not missing, ", ".join(missing))

fails = [n for n, ok in pins if not ok]
print(f"\nui_editor_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
