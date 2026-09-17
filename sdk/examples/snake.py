# SNAKE in the DXN1 STUDIO — the classic, on the engine's wire.
# run:  dxn3 sdk/examples/snake.py
# arrows / wasd steer · eat the reds, grow the tail · wall and tail bite.
from dxn3 import *
import random

CELL = 12
COLS, ROWS = W // CELL, H // CELL
background("#070b16")

hud = label("hud", 2, 2, "SNAKE  ·  arrows / wasd  ·  score 0")
food = circle("food", 0, 0, CELL, CELL, "#fb7185")
food.tag = "food"
food.glow = 3                          # the meal is the one thing that glows

body = []                    # entities, head first
life = 0                     # each life names its segments fresh — a name
score, step = 0, 0.0         # re-spawned AND retired in one frame would
dirx, diry, turns = 1, 0, [] # die twice (the engine applies set before del)
alive = True


def free_cell():
    """a cell no segment stands on — None when the snake IS the world."""
    if len(body) >= COLS * ROWS:
        return None
    while True:
        c = (random.randrange(COLS) * CELL, random.randrange(ROWS) * CELL)
        if all(seg.x != c[0] or seg.y != c[1] for seg in body):
            return c


def reset():
    global body, score, step, dirx, diry, turns, alive, life
    for seg in body:
        destroy(seg.name)
    life += 1
    midx, midy = (COLS // 2) * CELL, (ROWS // 2) * CELL
    body = [rect(f"seg{life}_{i}", midx - i * CELL, midy,
                 CELL - 2, CELL - 2, "#a78bfa" if i else "#8b5cf6")
            for i in range(3)]
    body[0].tag = "head"
    for seg in body[1:]:
        seg.tag = "body"
    score, step, dirx, diry, turns, alive = 0, 0.0, 1, 0, [], True
    hud.text = "SNAKE  ·  arrows / wasd  ·  score 0"
    cell = free_cell()
    if cell:
        food.x, food.y = cell


def on_key(k):
    if not alive:
        if k == "space":
            reset()
        return
    want = {"left": (-1, 0), "a": (-1, 0),
            "right": (1, 0), "d": (1, 0),
            "jump": (0, -1), "w": (0, -1), "space": (0, -1),
            "s": (0, 1)}.get(k)
    # a HELD key fires every frame — the queue would drown in stale
    # turns and steer the snake long after you changed your mind.
    # dedupe the tail and keep it three turns deep, the player's way.
    if want and turns[-1:] != [want]:
        turns.append(want)
        if len(turns) > 3:
            turns.pop(0)


RANKS = [(20, "the world eater"), (15, "the anaconda"),
         (10, "the hunter"), (5, "the garden snake")]


def rank(n):
    """a name for the length you have become — the honest ladder."""
    for need, title in RANKS:
        if n >= need:
            return title
    return "the hatchling"


def on_tick(dt2):
    global step, dirx, diry, score, alive
    if not alive:
        return
    step += dt2
    speed = max(0.06, 0.14 - score * 0.004)   # every meal sharpens the snake
    if step < speed:
        return
    step = 0.0
    while turns:                              # ONE honest turn per step
        dx, dy = turns.pop(0)
        if (dx, dy) != (-dirx, -diry):        # no instant self-bite
            dirx, diry = dx, dy
            break
    hx, hy = body[0].x + dirx * CELL, body[0].y + diry * CELL
    if hx < 0 or hy < 0 or hx > W - CELL or hy > H - CELL:
        alive = False
        win(f"the wall — score {score} · space for a new snake")
        print(f"the wall. score {score} — space for a new snake")
        return
    for seg in body[:-1]:                     # the tail vacates as you land
        if seg.x == hx and seg.y == hy:
            alive = False
            win(f"you bit yourself — score {score} · space for a new snake")
            print(f"you bit yourself. score {score} — space for a new snake")
            return
    tx, ty = body[-1].x, body[-1].y
    for i in range(len(body) - 1, 0, -1):     # the tail walks to the head
        body[i].x, body[i].y = body[i - 1].x, body[i - 1].y
    body[0].x, body[0].y = hx, hy
    if hx == food.x and hy == food.y:
        score += 1
        seg = rect(f"seg{life}_{len(body)}", tx, ty, CELL - 2, CELL - 2,
                   "#a78bfa")
        seg.tag = "body"
        body.append(seg)                      # the meal rides the tail
        body[0].flash = 1.0                   # the head bleaches white —
        if score % 5 == 0:                    #   milestones flash the tail too
            seg.flash = 0.8
        cell = free_cell()
        if cell:
            food.x, food.y = cell
        hud.text = f"SNAKE  ·  arrows / wasd  ·  score {score}"
        vars(score=score)
        # the meal speaks: milestones get a name, the rest a census
        if score % 5 == 0:
            say(f"{score} meals — you are {rank(score)} now")
        else:
            say(f"meal {score} · {len(body)} long")
        print(f"meal {score} — the snake is {len(body)} long")
    if len(body) >= COLS * ROWS:
        alive = False
        win("the snake IS the world — nothing left to eat. perfect")
        print("the snake IS the world. nothing left to eat — perfect")
        vars(score=score)


reset()
run()
