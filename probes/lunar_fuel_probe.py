#!/usr/bin/env python3
import os as _os
_HOME = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
# The probes COME HOME (v3.1.91): this pin lives in the repo now and the
# gates run it — a probe the gates never run ages into a liar (the drift
# ledger lives in probes/README.md). Canonical law pins: probes/*_probe.py.
# DS2-R33 probe: lunar.py "the tank wears the low light" — over the
# real wire (python SDK) at 960x540.
# pins: the gauge is born quiet (glow 0, fuel 100); a held main burn
# (14 fuel/s) walks the tank down and the glow rides the countdown —
# a faint ring (1) when the fuel first reads <= 30, BRIGHT (2) when
# it first reads <= 15, the burn holding through the dregs; the blink
# coexists with the light (a hidden bar still wears its glow); and a
# dry tank is a flat dark line (glow 0, w 0). The fuel is read from
# the bar's own honest width (fuel = w * 100 / 28).
import json, subprocess, sys, os

REPO = _HOME
os.environ["PYTHONPATH"] = f"{REPO}/sdk"
fails = []

def pin(name, ok, detail=""):
    print(("  ok  " if ok else " FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok: fails.append(name)

p = subprocess.Popen(["python3", f"{REPO}/sdk/examples/lunar.py"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     text=True, bufsize=1)

def child_line():
    ln = p.stdout.readline()
    if not ln.strip():
        return None
    try:
        return json.loads(ln)
    except json.JSONDecodeError:
        return child_line()          # console chatter rides bare

def send(o):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()

def tick(keys=None, dt=0.1):
    send({"t": "tick", "dt": dt,
          "keys": {k: True for k in (keys or [])},
          "chars": "", "hits": []})
    while True:
        pkt = child_line()
        if pkt is None:
            print("FAIL: child died"); sys.exit(1)
        if pkt.get("t") == "frame":
            return {e["name"]: e for e in pkt["set"]}, pkt

send({"t": "hello", "w": 960, "h": 540})
scene = child_line()
assert scene and scene.get("t") == "scene", f"no scene: {str(scene)[:120]}"
ents = {e["name"]: e for e in scene["entities"]}
pin("the gauge is born quiet (glow 0)", ents["fuelbar"].get("glow", 0) == 0,
    str(ents["fuelbar"].get("glow")))

fuel_of = lambda bar: bar["w"] * 100.0 / 28.0
seen_ring = None          # (fuel, glow) at the first reading <= 30
seen_bright = None        # (fuel, glow) at the first reading <= 15
seen_dregs_hold = True
seen_hidden_with_glow = False
dry = None                # (w, glow) at the first reading fuel <= 0.01
for i in range(200):
    ents, f = tick(keys=["space"])   # the main burn, held
    bar = ents["fuelbar"]
    fuel = fuel_of(bar)
    glow = bar.get("glow", 0)
    if seen_ring is None and fuel <= 30:
        seen_ring = (fuel, glow)
    if seen_bright is None and fuel <= 15:
        seen_bright = (fuel, glow)
    if seen_bright is not None and fuel > 0.01 and glow != 2:
        seen_dregs_hold = False
    if bar.get("visible", 1) == 0 and glow > 0:
        seen_hidden_with_glow = True
    if fuel <= 0.01 and dry is None:
        dry = (bar["w"], glow)
        break

pin("the ring arrives when the tank reads <= 30 (glow 1)",
    seen_ring is not None and seen_ring[1] == 1, str(seen_ring))
pin("the ring's reading is honest (30 >= fuel > 15)",
    seen_ring is not None and 15 < seen_ring[0] <= 30.001, str(seen_ring))
pin("the dregs burn BRIGHT when the tank reads <= 15 (glow 2)",
    seen_bright is not None and seen_bright[1] == 2, str(seen_bright))
pin("the dregs' reading is honest (0 < fuel <= 15)",
    seen_bright is not None and 0 < seen_bright[0] <= 15.001, str(seen_bright))
pin("the burn holds the brightness through the dregs", seen_dregs_hold)
pin("the blink hides the bar but not its light",
    seen_hidden_with_glow, "no hidden-with-glow frame seen")
pin("a dry tank is a flat dark line (w 0, glow 0)",
    dry is not None and dry[0] == 0 and dry[1] == 0, str(dry))

p.stdin.close()
print()
if fails:
    print(f"{len(fails)} PIN(S) FAILED: {fails}")
    sys.exit(1)
print("ALL PINS GREEN — the last fuel burns")
