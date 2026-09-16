"""dxn3 SDK — write a game in Python, the studio renders it.

    from dxn3 import *
    import random

    ship = rect("ship", W // 2, H - 10, 12, 5, "#8b5cf6")

    def on_key(k):          # held keys each frame: "left" "right" "jump" "space" + letters
        if k == "left": ship.x -= 1

    def on_tick(dt):        # every frame
        ...

    def on_hit(a, b):       # two tagged entities overlapping
        ...

    run()                   # hands the loop to the studio

The engine owns rendering, input and collision; this module talks the
line-JSON protocol on stdio. print() goes to the studio's console.
"""
import json
import sys

# the engine says hello before your module finishes importing — that is
# how W and H are ready for your very first line of code
try:
    _hello = json.loads(sys.stdin.readline())
    W = int(_hello.get("w", 100))
    H = int(_hello.get("h", 46))
except Exception:
    print("run me from the studio:  dxn3 mygame.py   (not directly)")
    sys.exit(1)

dt = 0.0                                    # seconds since last tick
E = {}                                      # name -> Ent
_scene = {"t": "scene", "name": "game", "bg": "#0b0e1a",
          "gravity": 0, "entities": []}
_dels = []
_vars = {}
_cam = {}
_ticks, _keys, _hits, _starts = [], [], [], []


class Ent:
    """one entity — attributes ARE the fields the engine renders."""
    def __init__(self, d):
        object.__setattr__(self, "d", d)
    def __getattr__(self, k):
        return self.d.get(k)
    def __setattr__(self, k, v):
        self.d[k] = v


def _send(o):
    sys.stdout.write(json.dumps(o) + "\n")
    sys.stdout.flush()


def _mk(name, d):
    d.setdefault("visible", 1)
    if name in E:
        # same name again = a redraw: replace the body in place (both in
        # the registry and the pending scene packet) instead of raising
        for i, old in enumerate(_scene["entities"]):
            if old.get("name") == name:
                _scene["entities"][i] = d
                break
    else:
        _scene["entities"].append(d)
    ent = Ent(d)
    E[name] = ent
    return ent


def rect(name, x, y, w, h, color="#8b5cf6"):
    return _mk(name, {"name": name, "shape": "rect", "x": x, "y": y,
                      "w": w, "h": h, "color": color})


def circle(name, x, y, w, h, color="#facc15"):
    return _mk(name, {"name": name, "shape": "circle", "x": x, "y": y,
                      "w": w, "h": h, "color": color})


def tri(name, x, y, w, h, color="#ef4444"):
    return _mk(name, {"name": name, "shape": "tri", "x": x, "y": y,
                      "w": w, "h": h, "color": color})


def label(name, x, y, text, color="#e9e5ff"):
    return _mk(name, {"name": name, "shape": "text", "x": x, "y": y,
                      "w": max(1, len(str(text))), "h": 2, "text": str(text),
                      "color": color})


def destroy(name):
    if name in E:
        del E[name]
        _dels.append(name)


def find(name):
    return E.get(name)


def background(hex_color):
    _scene["bg"] = hex_color


def gravity(g):
    _scene["gravity"] = g


def magnet(px_):
    _scene["magnet"] = px_


def camera(x, y, zoom=1):
    _cam.update(x=x, y=y, zoom=zoom)


def vars(**kw):
    _vars.update(kw)


def on_tick(fn): _ticks.append(fn); return fn
def on_key(fn): _keys.append(fn); return fn
def on_hit(fn): _hits.append(fn); return fn
def on_start(fn): _starts.append(fn); return fn


def run():
    """hand the loop to the studio. your plain `def on_tick(dt)`,
    `def on_key(k)`, `def on_hit(a, b)`, `def on_start()` are picked
    up automatically — no decorators, no ceremony."""
    global dt
    import inspect
    fg = inspect.stack()[1].frame.f_globals
    def _hook(name):
        fn = fg.get(name)                       # skip our own registrars
        return fn if callable(fn) and getattr(fn, "__module__", "") != __name__ else None
    ticks = _ticks + ([_hook("on_tick")] if _hook("on_tick") else [])
    keys_ = _keys + ([_hook("on_key")] if _hook("on_key") else [])
    hits_ = _hits + ([_hook("on_hit")] if _hook("on_hit") else [])
    starts = _starts + ([_hook("on_start")] if _hook("on_start") else [])
    _send(_scene)
    started = False
    _pairs = set()                             # overlap pairs already reported
    for line in sys.stdin:
        try:
            pkt = json.loads(line)
        except Exception:
            print(line[:200])               # engine chatter -> console
            continue
        if pkt.get("t") != "tick":
            continue
        dt = float(pkt.get("dt") or 0.0)
        fg["dt"] = dt               # the caller's dt stays fresh — a copied
        keys = pkt.get("keys", {})   # float from `import *` would freeze at 0
        if not started:
            for fn in starts:
                fn()
            started = True
        # physics-lite: velocities integrate unless you steer them
        for ent in list(E.values()):
            vx = ent.d.get("vx", 0)
            vy = ent.d.get("vy", 0)
            if vx:
                ent.d["x"] = ent.d.get("x", 0) + vx * dt
            if vy:
                ent.d["y"] = ent.d.get("y", 0) + vy * dt
        for fn in ticks:
            fn(dt)
        held = [k for k in ("left", "right", "jump", "space") if keys.get(k)]
        held += [c for c in str(pkt.get("chars", "")) if c.strip()]
        for k in held:
            for fn in keys_:
                fn(k)
        # hits arrive flat: [nameA, nameB, nameC, …]. fire on ENTER only —
        # a pair that separates may fire again; a held overlap never spams
        hs = pkt.get("hits", []) or []
        seen = set()
        for i in range(0, len(hs) - 1, 2):
            na, nb = str(hs[i]), str(hs[i + 1])
            pair = (na, nb) if na <= nb else (nb, na)
            seen.add(pair)
            if pair in _pairs:
                continue
            a = E.get(na)
            b = E.get(nb)
            if a is not None and b is not None:
                for fn in hits_:
                    fn(a, b)
        _pairs = seen
        _send({"t": "frame",
               "set": [e.d for e in E.values()],
               "del": _dels,
               "vars": _vars,
               "camera": _cam})
        _dels.clear()
        _vars.clear()
