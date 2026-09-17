# RAYCASTER in the DXN1 STUDIO — the engine is a canvas, so paint a world.
# run:  dxn3 sdk/examples/raycast.py
# a Wolfenstein-style 3D view out of plain rects: left/right turn,
# w/forward + s/back walk, a wall stops you, distance shades the world.
from dxn3 import *
import math

MAP = [
    "################",
    "#..............#",
    "#.####.....##..#",
    "#.#..........#.#",
    "#.#..###..#..#.#",
    "#.......#..#...#",
    "#.###..##......#",
    "#.....#....##..#",
    "#..#.....#...#.#",
    "#..#.##......#.#",
    "#..............#",
    "################",
]
MH, MW = len(MAP), len(MAP[0])
CELL = 64.0

background("#04060d")
hud = label("hud", 2, 2, "RAYCASTER · ←/→ turn · w/s walk · a map of rects")

FOV = math.pi / 3.0
px, py = 1.5 * CELL, 1.5 * CELL          # the eye — the open corridor's end
ang = 0.0
NCOL = max(24, min(110, W // 8))
COLW = W / NCOL

cols = [rect(f"c{i}", i * COLW, 0, COLW + 1, 1, "#8b5cf6") for i in range(NCOL)]
mark = rect("mark", 0, 0, 6, 6, "#facc15")   # where you stand, on the hud rail


def solid(mx, my):
    if mx < 0 or my < 0 or my >= MH or mx >= MW:
        return True
    return MAP[my][mx] == "#"


def shade(dist, wall_kind):
    # near walls burn violet, far walls sink into the dark
    t = max(0.0, min(1.0, 1.0 - dist / (9.0 * CELL)))
    if wall_kind == "x":                 # the two faces wear different tones
        r, g, b = int(90 + 120 * t), int(70 + 90 * t), int(200 + 55 * t)
    else:
        r, g, b = int(60 + 70 * t), int(45 + 55 * t), int(140 + 40 * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def on_key(k):
    global px, py, ang
    turn = 1.6 * dt
    walk = 150.0 * dt
    if k == "left":
        ang -= turn
    elif k == "right":
        ang += turn
    elif k in ("w", "jump"):
        nx, ny = px + math.cos(ang) * walk, py + math.sin(ang) * walk
        if not solid(int(nx // CELL), int(py // CELL)):
            px = nx
        if not solid(int(px // CELL), int(ny // CELL)):
            py = ny
    elif k in ("s",):
        nx, ny = px - math.cos(ang) * walk, py - math.sin(ang) * walk
        if not solid(int(nx // CELL), int(py // CELL)):
            px = nx
        if not solid(int(px // CELL), int(ny // CELL)):
            py = ny


def on_tick(dt2):
    mid = H // 2                          # the horizon lives mid-screen
    for i in range(NCOL):
        ray = ang - FOV / 2 + FOV * (i + 0.5) / NCOL
        step = 4.0                        # the marcher's stride (px)
        dist, kind = 1.0, "y"
        cx, cy = px, py
        sx, sy = math.cos(ray) * step, math.sin(ray) * step
        for _ in range(600):
            cx += sx
            cy += sy
            mx, my = int(cx // CELL), int(cy // CELL)
            if solid(mx, my):
                dist = math.hypot(cx - px, cy - py)
                kind = "x" if int((cx - sx) // CELL) != mx else "y"
                break
        # the taller the wall appears, the closer it stands
        hgt = min(float(H), (H * CELL) / max(dist, 1.0))
        c = cols[i]
        c.x = i * COLW
        c.y = mid - hgt / 2
        c.h = max(2.0, hgt)
        c.color = shade(dist, kind)
    mark.x = W - 12
    mark.y = 4


run()
