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
    ("the splash wears the v3 art (the R58 amendment) and the browser "
     "wears the campaign map",
        "assets/splash-v3.png" in html and 'id="cb-map"' in html
        and os.path.isfile(os.path.join(assets_dir, "splash-v3.png"))
        and os.path.isfile(os.path.join(assets_dir, "campaign-map.png"))),
]
missing = [nm for nm, ok in R48 if not ok]
pin("all 4 R48 studio laws present", not missing, ", ".join(missing))

# pin 16 — the R50 laws: THE PIE HUD — the game's face during play.
# The DOM overlay framed by the generated chrome (hud-frame.png +
# hud-panel.png — both raw JPEG, the JPEG-bytes law's 8th and 9th
# catches, re-encoded to real PNGs), the stat pills (score with the
# coin icon, the clock, deaths), the live spark telemetry bars (vx
# against PIESPEED, vy against gravity's 1500), the grounded/airborne
# state — switched on by startPlay, off by stopPlay, fed by drawSim at
# frame rate. Plus the palette's hover polish (the cards lift, the
# icons glow).
hud_frame = os.path.join(assets_dir, "hud-frame.png")
hud_panel = os.path.join(assets_dir, "hud-panel.png")
hud_magic = b""
if os.path.isfile(hud_panel):
    with open(hud_panel, "rb") as fh:
        hud_magic = fh.read(4)
R50 = [
    ("PIE HUD — the overlay exists and PIE switches it",
        'id="pie-hud"' in html
        and '$("pie-hud").classList.add("on")' in html
        and '$("pie-hud").classList.remove("on")' in html),
    ("PIE HUD — the pills are fed by the sim at frame rate",
        '$("hud-score").textContent' in html
        and '$("hud-time").textContent' in html
        and '$("hud-deaths").textContent' in html
        and '$("hud-vx").style.width' in html
        and '"grounded":"airborne"' in html),
    ("PIE HUD — wears the generated chrome (real PNGs)",
        "assets/hud-frame.png" in html and "assets/hud-panel.png" in html
        and os.path.isfile(hud_frame) and os.path.isfile(hud_panel)
        and hud_magic == b"\x89PNG"),
    ("palette hover — the cards lift and their icons glow",
        ".actor:hover .ic{box-shadow:" in html
        and "transform:translateY(-1px)" in html),
]
missing50 = [nm for nm, ok in R50 if not ok]
pin("all 4 R50 studio laws present", not missing50, ", ".join(missing50))

# pin 17 — the R51 laws: THE OUTLINER TREE (the entities group under
# their tag's collapsible folders, the fold state rides the prefs, the
# folder's own eye hides the whole group, a search flattens), THE
# CAMERA BOOKMARKS (Ctrl+1..9 saves the viewport camera, 1..9 recalls
# it, the desk modal mirrors the slots, the slots ride the prefs and
# sleep during PIE), and THE HUD SKINS (the PIE chrome follows the
# biome — keyed by scene file like the skies, three generated frames,
# the generic as fallback; the JPEG-bytes law's 10th-12th catches).
hud_skins = [f for f in ("hud-twilight.png", "hud-industrial.png",
                         "hud-void.png")
             if os.path.isfile(os.path.join(assets_dir, f))]
skin_magic = b""
if os.path.isfile(os.path.join(assets_dir, "hud-void.png")):
    with open(os.path.join(assets_dir, "hud-void.png"), "rb") as fh:
        skin_magic = fh.read(4)
R51 = [
    ("outliner tree — the tag folders fold and remember",
        "const groups=new Map();" in html
        and "S.olFolds[tg]=!S.olFolds[tg]" in html
        and 'folds:S.olFolds' in html
        and 'className="ol-folder"' in html and ".olrow.child{padding-left" in html),
    ("outliner tree — the folder eye hides the whole group",
        "members.forEach(e=>S.hidden.add(e.name))" in html),
    ("bookmarks — Ctrl+1..9 saves, 1..9 recalls, the desk mirrors",
        "S.bmarks[k]={x:S.cam.x,y:S.cam.y,z:S.cam.z}" in html
        and "camera recalled" in html
        and 'id="vp-bm"' in html and 'data-bm-go' in html
        and 'bmarks:S.bmarks' in html),
    ("bookmarks sleep during PIE (the digits are the game's)",
        "/^[1-9]$/.test(k)&&!S.sim" in html),
    ("HUD skins — the chrome follows the biome (real PNGs)",
        "const HSKINS={" in html and "HSKINS[S.cur]" in html
        and len(hud_skins) == 3 and skin_magic == b"\x89PNG"),
]
missing51 = [nm for nm, ok in R51 if not ok]
pin("all 5 R51 studio laws present", not missing51, ", ".join(missing51))

# pin 18 — the R52 laws: THE MIXED PILL (the multi-select Details grows
# UE5's per-property bulk edit: every property of the selection as a
# grid row, shared values edit in place, differing values wear the
# italic "Multiple Values" pill whose one click adopts a real editor
# that writes the whole selection), and THE DAWN HUD SKIN (the map's
# missing fourth biome frame, keyed by scene like its three siblings).
hud_dawn = os.path.join(assets_dir, "hud-dawn.png")
dawn_magic = b""
if os.path.isfile(hud_dawn):
    with open(hud_dawn, "rb") as fh:
        dawn_magic = fh.read(4)
R52 = [
    ("mixed pill — the multi-select property grid exists",
        "function mixedRow(" in html
        and 'pill.className="det-mixed"' in html
        and "Multiple Values" in html
        and ".det-mixed{" in html),
    ("mixed pill — the grid covers the transform and the cloth",
        'mixedRow(sel,"x","num"' in html
        and 'mixedRow(sel,"h","num"' in html
        and 'mixedRow(sel,"alpha","num"' in html
        and 'mixedRow(sel,"shape","select"' in html
        and 'mixedRow(sel,"solid","check"' in html),
    ("dawn HUD skin — the fourth biome frame (real PNG)",
        "hud-dawn.png" in html and os.path.isfile(hud_dawn)
        and dawn_magic == b"\x89PNG"),
    ("About modal — the credits splash wears the chrome and the skins",
        'class="about-wrap"' in html
        and 'class="about-skins"' in html
        and 'skin("hud-dawn.png","dawn")' in html
        and '.about-grid{' in html),
]
missing52 = [nm for nm, ok in R52 if not ok]
pin("all 4 R52 studio laws present", not missing52, ", ".join(missing52))


# ---- THE R53 LAWS ------------------------------------------------------
# THE TAB THUMBNAILS (every scene tab wears a live miniature of its own
# map — the biome sky tint, the entities fitted into a 76x44 canvas,
# redrawn from the scene's own geometry on every tab render AND on every
# edit of the active scene) and THE PLAYER PORTRAIT (the PIE HUD wears
# the generated hero bust in a rounded brand-violet frame with a live HP
# bar that bleeds with every death and is restored on the load).
portrait = os.path.join(assets_dir, "portrait-hero.png")
portrait_magic = b""
if os.path.isfile(portrait):
    with open(portrait, "rb") as fh:
        portrait_magic = fh.read(4)
R53 = [
    ("tab thumbnails — every tab carries a live miniature",
        "function thumbScene(" in html
        and 'th.className="vthumb"' in html
        and "thumbScene(f, th)" in html
        and ".vtab .vthumb{" in html),
    ("tab thumbnails — the tile follows the edit",
        "const THUMB_TINTS={" in html
        and "thumbScene(S.cur, th)" in html
        and '.querySelector("#tabbar .vtab.active .vthumb")' in html),
    ("player portrait — the PIE HUD wears the generated bust (real PNG)",
        "portrait-hero.png" in html
        and 'class="hud-portrait"' in html
        and ".hud-portrait img{" in html
        and os.path.isfile(portrait) and portrait_magic == b"\x89PNG"),
    ("player portrait — the HP bar bleeds and restores",
        'id="hud-hp"' in html
        and "hp.style.width" in html
        and "100-Math.min(90,m.deaths*15)" in html),
]
missing53 = [nm for nm, ok in R53 if not ok]
pin("all 4 R53 studio laws present", not missing53, ", ".join(missing53))


# ---- THE R54 LAWS ------------------------------------------------------
# THE CAMPAIGN MAP TILES (the Content Browser's banner is the campaign
# itself — four biome tiles sliced from the generated strip, tinted, the
# live entity count on each, the active scene's biome glowing), THE GOAL
# FLAG'S SHIMMER (two sweep bands + the breathing glow, one draw shared
# by the editor viewport and PIE), THE PORTRAIT SHEET (the HUD's bust
# follows the biome — one hero, four lit variants, all real PNGs), and
# THE ABOUT CAST (the splash wears the whole sheet).
def _png_magic(name):
    p = os.path.join(assets_dir, name)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as fh:
        return fh.read(4)

R54 = [
    ("campaign map — the banner is four live biome tiles",
        "function buildCampaignMap(" in html
        and "const BIOMES=[" in html
        and html.count('img:"header-') >= 4
        and "buildCampaignMap();" in html
        and "#cb-map .biome.active{" in html),
    ("campaign map — the tiles wear the generated headers (R55)",
        "background-size:cover" in html
        and "url('assets/${bm.img}')" in html
        and "n} ents</em>`" in html.replace("\n", " ")
        and "loadScene(f); });" in html),
    ("goal shimmer — the sweeps and the breathing glow, one shared draw",
        "function drawGoalShimmer(" in html
        and 'if(e.tag==="goal") drawGoalShimmer(sx,sy,w,h);' in html
        and 'if(tagOf(e)==="goal") drawGoalShimmer(sx,sy,w,h);' in html
        and "cx.shadowColor=" in html),
    ("portrait sheet — the HUD bust follows the biome (four real PNGs)",
        "const PHSKINS={" in html
        and 'PHSKINS[S.cur]||"portrait-hero.png"' in html
        and all((_png_magic(n) or b"") == b"\x89PNG" for n in (
            "portrait-industrial.png", "portrait-twilight.png",
            "portrait-dawn.png", "portrait-void.png"))),
    ("About cast — the splash wears the whole sheet",
        'skin("portrait-hero.png","the hero")' in html
        and html.count('skin("portrait-') >= 4
        and html.count('class="about-skins"') >= 2),
]
missing54 = [nm for nm, ok in R54 if not ok]
pin("all 5 R54 studio laws present", not missing54, ", ".join(missing54))


# ---- THE R55 LAWS ------------------------------------------------------
# THE BIOME HEADERS (each campaign tile wears its own generated wide
# banner — four real PNGs, the JPEG-bytes law's 16th catch, re-encoded)
# and THE VAULT DRAFT is pinned by absence: the tour's HOPS stays at
# level-5 until the ferry crossing walks green (the dec_vault draft
# rides in the tree, dormant behind the break-at-last-hop law).
R55 = [
    ("biome headers — the four generated banners are real PNGs",
        all((_png_magic(n) or b"") == b"\x89PNG" for n in (
            "header-twilight.png", "header-industrial.png",
            "header-dawn.png", "header-void.png"))
        and all(os.path.getsize(os.path.join(assets_dir, n)) > 10000
                for n in ("header-twilight.png", "header-industrial.png",
                          "header-dawn.png", "header-void.png"))),
    ("biome headers — the About cast wears the sheet too",
        html.count('skin("portrait-') >= 4
        and 'skin("portrait-hero.png","the hero")' in html),
    ("the vault draft — dormant, the tour's HOPS unchanged",
        "the vault (level-5)" in open(
            os.path.join(os.path.dirname(assets_dir), "..",
                         "probes", "grand_tour_probe.py"),
            "rb").read().decode(errors="replace")
        if os.path.isfile(os.path.join(os.path.dirname(assets_dir), "..",
                                       "probes", "grand_tour_probe.py"))
        else False),
]
missing55 = [nm for nm, ok in R55 if not ok]
pin("all 3 R55 studio laws present", not missing55, ", ".join(missing55))


# ---- THE R56 LAWS ------------------------------------------------------
# THE BIOME MAP COMPLETION (level-11 — "the return" — wears the void in
# all four maps: sky, hud, portrait, campaign tile), THE PIE AMBIENT
# FRAME (the viewport breathes with the biome's light and brightens as
# the spark nears the goal), THE BIOME FOOT (every tab thumbnail wears
# its biome's accent edge), and THE CREDITS TICKER (the grand tour's
# five walked scenes ride the generated journey panorama in the About
# splash — the JPEG-bytes law's 17th catch, re-encoded real PNG).
R56 = [
    ("level-11 mapped — the return wears the void in all four maps",
        '"level-11.dxn1.json":"sky-void.png"' in html
        and '"level-11.dxn1.json":"hud-void.png"' in html
        and '"level-11.dxn1.json":"portrait-void.png"' in html
        and 'level-10.dxn1.json","level-11.dxn1.json"]' in html),
    ("the PIE ambient frame — the biome's breath, the goal's call",
        "function drawAmbientFrame(" in html
        and "drawAmbientFrame();" in html
        and "const BIOME_ACC={" in html
        and html.count('const BIOME_ACC={') == 1
        and '"hud-void.png":"56,189,248"' in html),
    ("the biome foot — every tab thumbnail wears its accent edge",
        "const BIOME_FOOT={" in html
        and "g.fillStyle=BIOME_FOOT[SKYS[f]||" in html
        and "g.fillRect(0,H-2,W,2);" in html),
    ("the credits ticker — the tour rides the generated panorama",
        ".about-ticker" in html and "@keyframes tourride" in html
        and "function mountAboutTicker(" in html
        and "mountAboutTicker();" in html
        and 'id="about-ticker"' in html),
    ("the ticker's panorama is a real PNG",
        (_png_magic("tour-marquee.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "tour-marquee.png")) > 50000),
    ("PIE clears every frame — the sim loop renders through draw()",
        "simStep(dt); draw();" in html
        and "if(S.grid&&!S.sim){" in html.replace(" ", "")
        and "if(!S.sim){\n  const [ox,oy]=world2scr(0,0);" in html),
]
missing56 = [nm for nm, ok in R56 if not ok]
pin("all 6 R56 studio laws present", not missing56, ", ".join(missing56))


# ---- THE R57 LAWS ------------------------------------------------------
# THE COIN ROW (the PIE HUD wears the collectibles themselves — one
# generated coin per coin entity, dim until taken, a pop of light as it
# does; the JPEG-bytes law's 18th catch, re-encoded to a real circular
# PNG) and THE TILE FOOT (the campaign map's four tiles wear the same
# biome accent the tab thumbnails do — FOOT_BY_BIOME is DERIVED from
# BIOME_FOOT, so the two wears can never drift apart).
R57 = [
    ("the coin row — the PIE HUD's collectible ledger",
        "function buildCoinRow(" in html
        and "buildCoinRow(S.sim);" in html
        and 'id="hud-coinrow"' in html
        and 'img.classList.toggle("got", m.coins.has(img.dataset.n));' in html
        and 'lab.textContent="0/"+coins.length;' in html),
    ("the coin sprite — a real PNG (the JPEG-bytes law's 18th catch)",
        (_png_magic("coin-glow.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "coin-glow.png")) > 10000),
    ("the tile foot — the campaign map wears the biome accent",
        '#cb-map .biome::after{content:"";' in html
        and 'el.style.setProperty("--foot", FOOT_BY_BIOME[bm.b]||"#8b5cf6");' in html
        and "const FOOT_BY_BIOME={};" in html
        and html.count("const BIOME_FOOT={") == 1),
]
missing57 = [nm for nm, ok in R57 if not ok]
pin("all 3 R57 studio laws present", not missing57, ", ".join(missing57))


# THE R58 LAW GROUP — THE COIN POP (the take lands as a gold burst: a
# one-shot keyframe on the lit coin, not a plain fade), THE VAULT CARD
# (the About grid's fifth pillar wears the generated coin sprite as its
# badge — the vault summit's own card), and THE SPLASH V3 (the boot
# splash wears the generated vault key art — the JPEG-bytes law's 19th
# catch, re-encoded to a real PNG).
R58 = [
    ("the coin pop — the take lands as a one-shot gold burst",
        "@keyframes coinpop{" in html
        and "animation:coinpop .42s" in html
        and "42%{transform:scale(1.55);" in html),
    ("the vault card — the About grid's fifth pillar wears the coin",
        'class="about-card"><img class="ab-coin" src="assets/coin-glow.png"' in html
        and "<b>The Vault</b>" in html
        and ".about-card .ab-coin{width:20px;" in html),
    ("the splash v3 — the boot wears the generated vault key art (the "
     "JPEG-bytes law's 19th catch)",
        'src="assets/splash-v3.png"' in html
        and (_png_magic("splash-v3.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "splash-v3.png")) > 500000),
]
missing58 = [nm for nm, ok in R58 if not ok]
pin("all 3 R58 studio laws present", not missing58, ", ".join(missing58))


# THE R59 LAW GROUP — THE DEATH FLASH (the portrait takes the hit: a
# one-shot red pulse on every death, fired from die() through the
# reflow restart) and THE POP'S TINT (the coin burst wears the biome's
# own accent from BIOME_ACC — one map, one truth with the ambient
# frame) and THE ASCENT PORTRAIT (level-6's PIE bust is the generated
# climber — the JPEG-bytes law's 20th catch, re-encoded real PNG).
R59 = [
    ("the death flash — the portrait pulses red on every death",
        ".hud-portrait.hurt{animation:hurtflash .5s ease-out;}" in html
        and "@keyframes hurtflash{" in html
        and 'const port=document.querySelector(".hud-portrait");' in html
        and 'port.classList.add("hurt");' in html),
    ("the pop's tint — the coin burst wears the biome accent",
        "filter:drop-shadow(0 0 14px var(--pop," in html
        and 'row.style.setProperty("--pop","rgba("+(BIOME_ACC[HSKINS[S.cur]]||"251,191,36")+",.95)");' in html),
    ("the ascent portrait — level-6's PIE bust is generated art (the "
     "JPEG-bytes law's 20th catch)",
        '"level-6.dxn1.json":"portrait-ascent.png"' in html
        and (_png_magic("portrait-ascent.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "portrait-ascent.png")) > 500000),
]
missing59 = [nm for nm, ok in R59 if not ok]
pin("all 3 R59 studio laws present", not missing59, ", ".join(missing59))


# THE R60 LAW GROUP — THE HUD ROW SHAKE (the whole row takes the hit:
# .hud.hurt rattles once through the same reflow restart, the one-shot
# decayed screenshake discipline) and THE ATLAS CLOTH (the Content
# Browser's grid sits on the generated embroidered atlas — the
# JPEG-bytes law's 21st catch, re-encoded real PNG) and THE CAST'S
# SIXTH FACE (the ascent portrait joins the About sheet) and THE
# TICKER'S SIXTH HOP (level-6 rides the credits marquee).
R60 = [
    ("the hud row shake — the whole PIE HUD rattles on death",
        "#pie-hud.hurt{animation:hudshake .42s cubic-bezier(.36,.07,.19,.97);}" in html
        and "@keyframes hudshake{" in html
        and 'const row=port&&port.closest("#pie-hud");' in html
        and 'row.classList.add("hurt");' in html),
    ("the atlas cloth — the Content Browser's grid wears generated art "
     "(the JPEG-bytes law's 21st catch)",
        'url("assets/atlas-cloth.png")' in html
        and (_png_magic("atlas-cloth.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "atlas-cloth.png")) > 1000000),
    ("the cast's sixth face — the ascent portrait joins the About sheet",
        'skin("portrait-ascent.png","the ascent")' in html),
    ("the ticker's sixth hop — level-6 rides the credits marquee",
        'hops=["level-1.dxn1.json","level-2.dxn1.json","level-3.dxn1.json",'
        '"level-4.dxn1.json","level-5.dxn1.json","level-6.dxn1.json"]' in html),
]
missing60 = [nm for nm, ok in R60 if not ok]
pin("all 4 R60 studio laws present", not missing60, ", ".join(missing60))


# THE R61 LAW GROUP — THE TYPE CHIPS (UE5's outliner type filter: the
# census-honest chip row, one click narrows the tree to one tag) and
# THE MAGNET FIELD (the World Settings writes the scene json's magnet —
# the key spark reads with a 0 default) and THE PILLARS' SPLIT-SCREEN
# (the four biome cards wear their own panel of the generated
# four-world banner — the JPEG-bytes law's 22nd catch, re-encoded real
# PNG).
R61 = [
    ("the outliner's type chips — the census-honest filter row",
        '<div id="ol-chips"></div>' in html
        and ".olchip.on{background:#4a3a20; color:var(--text); border-color:var(--sel);}" in html
        and 'S.olType=t; renderOutliner();' in html
        and '(S.olType==="all"||(tagOf(e)||"solid")===S.olType)' in html),
    ("the World Settings' coin-magnet field — the json key spark reads",
        'numField("coin magnet",()=>sc.magnet||0,' in html
        and 'sc.magnet=Math.max(0,Math.round(v+dv));' in html
        and 'magnet <b>${sc.magnet||0}</b> px' in html),
    ("the pillars' split-screen — the four cards wear the generated "
     "four-world banner (the JPEG-bytes law's 22nd catch)",
        '.about-card.biomeback{background-size:400% 100%;' in html
        and 'url("assets/pillars-split.png")' in html
        and 'class="about-card biomeback"' in html
        and (_png_magic("pillars-split.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "pillars-split.png")) > 500000),
]
missing61 = [nm for nm, ok in R61 if not ok]
pin("all 3 R61 studio laws present", not missing61, ", ".join(missing61))

# THE R62 LAW GROUP — THE FLY-CAM (UE5's viewport discipline: RMB arms,
# WASDQE flies, the camera-speed pill governs) and THE SPLASH ROTATION
# (four generated splashes, v4 the vault-mouth scene — the JPEG-bytes
# law's 23rd catch, re-encoded real PNG).
R62 = [
    ("the fly-cam — RMB arms, WASDQE flies, the law owns the keys",
        'function flyStart(){' in html
        and 'if(S.fly.active&&["w","a","s","d","q","e"].includes(ev.key.toLowerCase())){' in html
        and 'ev.stopImmediatePropagation();   // the fly owns WASDQE while RMB is held' in html
        and 'if(ev.button===2) flyStart();   // RMB arms the fly (WASDQE live while held)' in html
        and 'if(ev.button===2) flyStop();   // RMB released: the fly disarms' in html
        and 'cv.addEventListener("contextmenu",ev=>ev.preventDefault());' in html),
    ("the camera-speed pill — the fly's governor rides the prefs",
        '<span class="vpill" id="vp-camspeed"' in html
        and 'const CAMSTEPS=[150,300,600,1200,2400];' in html
        and 'function setCamSpeed(v){ S.camSpeed=v; $("camspd").textContent=v; savePrefs(); }' in html
        and 'camSpeed:S.camSpeed,' in html
        and 'if(p.camSpeed>0) S.camSpeed=p.camSpeed;' in html
        and '$("vp-camspeed").classList.add("on");' in html),
    ("the splash rotation — the fourth splash is real PNG bytes",
        'const SPLASHES=["assets/splash.png","assets/splash-v2.png","assets/splash-v3.png","assets/splash-v4.png"];' in html
        and 'h.src=SPLASHES[Math.floor(Math.random()*SPLASHES.length)];' in html
        and (_png_magic("splash-v4.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "splash-v4.png")) > 400000),
]
missing62 = [nm for nm, ok in R62 if not ok]
pin("all 3 R62 studio laws present", not missing62, ", ".join(missing62))

# THE R63 LAW GROUP — THE LOOK-SENS PILL (the fly look's pitch/yaw
# pairing with the speed pill: click cycles, the wheel fine-tunes, the
# value rides the prefs, the pill glows while armed, the armed look is
# scaled — the MMB pan stays 1:1) and THE ASCENT'S OWN BIOME (level-6
# stops borrowing the industrial set — the generated indigo sky +
# chrome, the JPEG-bytes law's 24th and 25th catches, re-encoded real
# PNGs, the light-indigo accent wired).
R63 = [
    ("the look-sens pill — the fly look's governor rides the prefs",
        '<span class="vpill" id="vp-looksen"' in html
        and 'const LOOKSTEPS=[0.5,1,2,4];' in html
        and 'function setLookSens(v){ S.lookSens=v; $("looksens").textContent=v.toFixed(1); savePrefs(); }' in html
        and 'lookSens:S.lookSens,' in html
        and 'if(p.lookSens>0) S.lookSens=p.lookSens;' in html
        and '$("vp-looksen").classList.add("on");' in html),
    ("the armed look is scaled by the Look pill (the MMB pan stays 1:1)",
        'const lk=S.fly.active?S.lookSens:1;' in html
        and 'S.cam.x-=ev.movementX*lk/S.cam.z; S.cam.y-=ev.movementY*lk/S.cam.z; draw(); return;' in html),
    ("the ascent's own biome — level-6 wears its generated sky + chrome",
        '"level-6.dxn1.json":"sky-ascent.png",' in html
        and '"level-6.dxn1.json":"hud-ascent.png",' in html
        and '"hud-ascent.png":"129,140,248",' in html
        and (_png_magic("sky-ascent.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "sky-ascent.png")) > 400000
        and (_png_magic("hud-ascent.png") or b"") == b"\x89PNG"
        and os.path.getsize(os.path.join(assets_dir, "hud-ascent.png")) > 400000),
]
missing63 = [nm for nm, ok in R63 if not ok]
pin("all 3 R63 studio laws present", not missing63, ", ".join(missing63))


fails = [n for n, ok in pins if not ok]
print(f"\nui_editor_probe: {len(pins)-len(fails)}/{len(pins)} pins green "
      f"in {time.time()-t0:.1f}s")
sys.exit(1 if fails else 0)
