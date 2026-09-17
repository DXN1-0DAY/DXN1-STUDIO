#!/usr/bin/env python3
"""gate 6: every shipped example speaks the protocol — for real.

A fake engine feeds each sdk/examples game a hello + ticks and checks
the scene and frames come back. python + node + a compiled C++ game;
each probed only when its runner exists on this machine. Honest skips.
"""
import json, subprocess, sys, os, time, shutil, tempfile, random, math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDK = os.path.join(BASE, "sdk")
EX = os.path.join(SDK, "examples")


def have(exe):
    return shutil.which(exe) is not None


# ── the invaders' sky: one stream per concern, on the gate's wire ────
# The fleet's stars are born from THEIR OWN seeded stream (FNV-1a +
# xorshift32 over "the night sky" — the dino's law; the march's
# unseeded dice never touch it), so gate 6 predicts the deal from the
# replicated stream and the wire must agree EXACTLY — the same
# promotion the shooter's respawn earned. THE FLOAT TRAP: JS
# multiplies in float64 (seed * 16777619 exceeds 2^53 and ToUint32
# keeps only the exact float's low bits), so the replication XORs in
# int32, multiplies in float, truncates — never clean int math.
def _to_int32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x >= 0x80000000 else x


def _to_uint32_f(x):
    return int(math.fmod(x, 4294967296.0)) % 4294967296


def invaders_sky_deal():
    """the nine (x, y) seats the night sky deals, in birth order"""
    seed = 2166136261
    for ch in "the night sky":
        seed = _to_uint32_f(float(_to_int32(seed) ^ ord(ch)) * 16777619.0)

    def nnext():
        nonlocal seed
        seed = (seed ^ ((seed << 13) & 0xFFFFFFFF)) & 0xFFFFFFFF
        seed = (seed ^ (seed >> 17)) & 0xFFFFFFFF
        seed = (seed ^ ((seed << 5) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return seed / 4294967296

    out = []
    for _ in range(9):
        out.append((2 + math.floor(nnext() * (120 - 6)),
                    3 + math.floor(nnext() * 9)))
    return out


def probe(cmd, ticks=6, hold=None, hits=None, capture_at=None):
    """run a child game, feed hello+ticks, return (scene, frames, console).

    capture_at: when set, the frame packet sent at that tick index has
    its entity set parked in out["captured"] — a name -> patch dict —
    so a check can read the exact state a game put on the wire.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = SDK
    env["NODE_PATH"] = SDK
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, cwd=BASE, text=True,
                         bufsize=1, env=env)
    out = {"scene": None, "frames": 0, "console": [], "captured": {}}

    def send(o):
        try:
            p.stdin.write(json.dumps(o) + "\n")
            p.stdin.flush()
        except BrokenPipeError:
            pass                    # the game died — the check reports it

    def drain(until_frame, tmo=8.0):
        end = time.time() + tmo
        while time.time() < end:
            line = p.stdout.readline()
            if not line:
                return
            line = line.strip()
            if not line:
                continue
            try:
                pkt = json.loads(line)
            except Exception:
                out["console"].append(line[:160])
                continue
            t = pkt.get("t")
            if t == "scene" and out["scene"] is None:
                out["scene"] = pkt
            elif t == "frame":
                out["frames"] += 1
                if capture_at is not None and out["frames"] == capture_at:
                    out["captured"] = {e.get("name"): e
                                       for e in pkt.get("set", [])}
            else:
                out["console"].append(line[:160])
            if until_frame:
                if t == "frame":
                    return
            else:
                return                    # one packet is enough to answer

    try:
        send({"t": "hello", "w": 120, "h": 44})
        drain(False)
        for i in range(ticks):
            send({"t": "tick", "dt": 0.016,
                  "keys": {hold: True} if hold and i == 1 else {},
                  "chars": "",
                  "hits": hits if hits and i == 2 else []})
            drain(True)
    finally:
        p.kill()
    return (out["scene"], out["frames"], out["console"], out["captured"])


def main():
    fails = 0

    def check(name, ok, detail):
        nonlocal fails
        print(f"   {chr(111)+chr(107)+chr(32)+chr(32) if ok else chr(70)+chr(65)+chr(73)+chr(76)} {name}: {detail}", flush=True)
        if not ok:
            fails += 1

    py_games = [("background.py", ["python3", f"{EX}/background.py"], 3),
                ("shooter.py", ["python3", f"{EX}/shooter.py"], 15),
                ("flappy.py", ["python3", f"{EX}/flappy.py"], 11),
                ("cards.py", ["python3", f"{EX}/cards.py"], 12),
                ("snake.py", ["python3", f"{EX}/snake.py"], 5),
                ("lunar.py", ["python3", f"{EX}/lunar.py"], 11),
                ("raycast.py", ["python3", f"{EX}/raycast.py"], 26),
                ("windmill.py", ["python3", f"{EX}/windmill.py"], 13)]
    if have("python3"):
        for name, cmd, ents in py_games:
            scene, frames, console, captured = probe(cmd)
            got = len(scene.get("entities", [])) if scene else 0
            check(name, scene is not None and frames >= 3 and got == ents,
                  f"scene={'yes' if scene else 'NO'} frames={frames} "
                  f"entities={got}")
    else:
        print("   (skip) python3 games — python3 not on this machine", flush=True)

    if have("node"):
        scene, frames, console, captured = probe(["node", f"{EX}/bounce.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("bounce.js", scene is not None and frames >= 3 and got == 21,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console, captured = probe(["node", f"{EX}/asteroids.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("asteroids.js", scene is not None and frames >= 3 and got == 7,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console, captured = probe(["node", f"{EX}/invaders.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("invaders.js", scene is not None and frames >= 3 and got == 62,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        if scene:
            ents = {e.get("name"): e for e in scene.get("entities", [])}
            exp_deal = invaders_sky_deal()
            got_deal = [(ents.get(f"star-{i}", {}).get("x"),
                         ents.get(f"star-{i}", {}).get("y"))
                        for i in range(9)]
            check("invaders.js sky = its named stream's deal",
                  got_deal == exp_deal,
                  f"got={got_deal[:3]}... exp={exp_deal[:3]}...")
            alphas = [ents.get(f"star-{i}", {}).get("alpha") for i in range(9)]
            check("invaders.js stars born a rumor (alpha 0.15)",
                  all(a is not None and abs(a - 0.15) < 1e-9
                      for a in alphas),
                  f"alphas={alphas[:3]}...")
            moon = ents.get("moon", {})
            check("invaders.js moon born a whisper (0.25, unlit)",
                  moon.get("x") == 120 - 15 and moon.get("y") == 4 and
                  abs((moon.get("alpha") or 0) - 0.25) < 1e-9 and
                  moon.get("glow", 0) == 0,
                  f"moon={moon}")
        scene, frames, console, captured = probe(["node", f"{EX}/dino.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("dino.js", scene is not None and frames >= 3 and got == 24,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console, captured = probe(["node", f"{EX}/tetris.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("tetris.js", scene is not None and frames >= 3 and got == 23,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console, captured = probe(["node", f"{EX}/lightbot.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("lightbot.js", scene is not None and frames >= 3 and got == 38,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
    else:
        print("   (skip) bounce.js — node not on this machine", flush=True)

    if have("g++"):
        tmp = tempfile.mkdtemp(prefix="dxn3-gate6-")
        bin_ = os.path.join(tmp, "pong")
        build = subprocess.run(["g++", "-std=c++23", "-O2",
                                f"{EX}/pong.cpp", "-o", bin_],
                               capture_output=True, text=True)
        if build.returncode == 0:
            # a real hit pair: pad vs ball — the enter-only onHit must steer
            scene, frames, console, captured = probe([bin_], hold="w", hits=["ball", "pad"])
            got = len(scene.get("entities", [])) if scene else 0
            check("pong.cpp (compiled)", scene is not None and frames >= 3
                  and got == 5,
                  f"scene={'yes' if scene else 'NO'} frames={frames} "
                  f"entities={got}")
        else:
            check("pong.cpp (compiled)", False,
                  "build failed: " + build.stderr.strip()[:120])
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("   (skip) pong.cpp — g++ not on this machine", flush=True)

    # the NAMED-STREAM LAW, pinned in the gate itself: a seeded game's
    # respawn must be exactly what its own stream deals. The shooter is
    # the template — fire one bolt, land it on the enemy, and the
    # respawn's x/y ride the hit frame (the hit-pair timing contract:
    # on_hit runs after on_tick, the mutated entity speaks this frame).
    if have("python3"):
        scene, frames, console, cap = probe(
            ["python3", f"{EX}/shooter.py"], ticks=3, hold="space",
            hits=["shot1", "enemy"], capture_at=3)
        th = random.Random("the threat's return")
        exp = (th.randint(2, 120 - 14), th.randint(2, 44 // 2))
        en = cap.get("enemy")
        check("shooter.py respawn = its named stream's draw",
              en is not None and en.get("x") == exp[0]
              and en.get("y") == exp[1],
              f"got=({en.get('x') if en else None},"
              f"{en.get('y') if en else None}) "
              f"exp=({exp[0]},{exp[1]})")
    else:
        print("   (skip) named-stream law — python3 not on this machine",
              flush=True)

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
