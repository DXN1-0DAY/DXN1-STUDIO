# BALATRO-ISH — a card game proves the engine is not just platformers.
# five cards fan out; A/D select, SPACE plays the selected card. chips x
# mult scoring, the selected card GLOWS, a played card FLASHES white as
# it lands — and the flash DECAYS down the honest staircase (a card
# that stayed white forever was the light lying; the studio keeps
# whatever the game last sent, so the decay is the GAME's job).
# the whole hand GHOSTS IN on one shared clock (cards and their ranks
# together — the radar-field law), a PLAYED card wears alpha 0.5 (the
# hand remembers what it spent), and a red card's double pay SPEAKS:
# the title glows 3 and cools at six a second. no physics, pure state.
# run:  dxn3 sdk/examples/cards.py
from dxn3 import *

background("#0d1b12")
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
SUITS = ["♠", "♥", "♦", "♣"]
selected, played, chips, mult = 0, [], 0, 1
ghostT = 0.0                                         # the hand arrives as ghosts

deck = label("title", 2, 1, "BLATRO — A/D select · SPACE play · score: 0 x 1")
hand_lbl = label("hand", 2, 3, "hand: —")
cards = []

for i in range(5):                                   # the draw
    rank = RANKS[(i * 3 + 1) % len(RANKS)]
    suit = SUITS[i % len(SUITS)]
    x = W // 2 - 24 + i * 10
    c = rect(f"card{i}", x, H // 2 - 4, 9, 7, "#1f2937")
    t = label(f"ct{i}", x + 1, H // 2 - 3, rank + suit,
              "#facc15" if suit in "♥♦" else "#e9e5ff")
    cards.append((c, t, rank, suit))

def redraw():
    A = 0.15 + 0.85 * ghostT                         # the radar-field law
    for i, (c, t, rank, suit) in enumerate(cards):
        c.color = "#facc15" if i == selected else "#1f2937"
        c.glow = 6 if i == selected else 0            # the glow hand
        t.y = (H // 2 - 5) if i == selected else (H // 2 - 3)
        spent = (rank + suit) in played
        c.alpha = 0.5 if spent else A                 # the hand remembers
        t.alpha = c.alpha                             # the rank wears it too

def on_key(k):
    global selected, chips, mult
    if k == "left":  selected = (selected - 1) % len(cards)
    if k == "right": selected = (selected + 1) % len(cards)
    if k == "space":
        c, t, rank, suit = cards[selected]
        if suit in "♥♦":                              # red pays double
            chips += 4
            mult += 1
            deck.glow = 3                             # the bounty speaks
        else:
            chips += 2
        c.flash = 1.0                                 # the landing flash
        t.text = t.text + " ✓"
        played.append(rank + suit)
        hand_lbl.text = "hand: " + (" ".join(played) if played else "—")
        deck.text = f"BLATRO — played {rank}{suit} · score: {chips} x {mult}"
        print("played", rank + suit, "chips", chips, "mult", mult)

def on_tick(dt2):
    global ghostT
    ghostT = min(1.0, ghostT + dt2 / 0.9)     # one clock for the whole hand
    for c, t, rank, suit in cards:
        if c.flash:
            c.flash = max(0.0, c.flash - 3 * dt2)     # the flash decays honestly
    deck.glow = max(0.0, (deck.glow or 0.0) - 6 * dt2)   # the bounty cools
    redraw()

run()
