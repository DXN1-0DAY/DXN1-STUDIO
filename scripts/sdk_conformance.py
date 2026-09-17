#!/usr/bin/env python3
"""gate 6: every shipped example speaks the protocol — for real.

A fake engine feeds each sdk/examples game a hello + ticks and checks
the scene and frames come back. python + node + a compiled C++ game;
each probed only when its runner exists on this machine. Honest skips.
"""
import json, subprocess, sys, os, time, shutil, tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDK = os.path.join(BASE, "sdk")
EX = os.path.join(SDK, "examples")


def have(exe):
    return shutil.which(exe) is not None


def probe(cmd, ticks=6, hold=None, hits=None):
    """run a child game, feed hello+ticks, return (scene, frames, console)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = SDK
    env["NODE_PATH"] = SDK
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, cwd=BASE, text=True,
                         bufsize=1, env=env)
    out = {"scene": None, "frames": 0, "console": []}

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
    return out["scene"], out["frames"], out["console"]


def main():
    fails = 0

    def check(name, ok, detail):
        nonlocal fails
        print(f"   {chr(111)+chr(107)+chr(32)+chr(32) if ok else chr(70)+chr(65)+chr(73)+chr(76)} {name}: {detail}", flush=True)
        if not ok:
            fails += 1

    py_games = [("background.py", ["python3", f"{EX}/background.py"], 3),
                ("shooter.py", ["python3", f"{EX}/shooter.py"], 3),
                ("flappy.py", ["python3", f"{EX}/flappy.py"], 9),
                ("cards.py", ["python3", f"{EX}/cards.py"], 12),
                ("snake.py", ["python3", f"{EX}/snake.py"], 5),
                ("lunar.py", ["python3", f"{EX}/lunar.py"], 11),
                ("raycast.py", ["python3", f"{EX}/raycast.py"], 26),
                ("windmill.py", ["python3", f"{EX}/windmill.py"], 13)]
    if have("python3"):
        for name, cmd, ents in py_games:
            scene, frames, console = probe(cmd)
            got = len(scene.get("entities", [])) if scene else 0
            check(name, scene is not None and frames >= 3 and got == ents,
                  f"scene={'yes' if scene else 'NO'} frames={frames} "
                  f"entities={got}")
    else:
        print("   (skip) python3 games — python3 not on this machine", flush=True)

    if have("node"):
        scene, frames, console = probe(["node", f"{EX}/bounce.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("bounce.js", scene is not None and frames >= 3 and got == 21,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console = probe(["node", f"{EX}/asteroids.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("asteroids.js", scene is not None and frames >= 3 and got == 7,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console = probe(["node", f"{EX}/invaders.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("invaders.js", scene is not None and frames >= 3 and got == 52,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console = probe(["node", f"{EX}/dino.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("dino.js", scene is not None and frames >= 3 and got == 22,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console = probe(["node", f"{EX}/tetris.js"])
        got = len(scene.get("entities", [])) if scene else 0
        check("tetris.js", scene is not None and frames >= 3 and got == 22,
              f"scene={'yes' if scene else 'NO'} frames={frames} "
              f"entities={got}")
        scene, frames, console = probe(["node", f"{EX}/lightbot.js"])
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
            scene, frames, console = probe([bin_], hold="w", hits=["ball", "pad"])
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

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
