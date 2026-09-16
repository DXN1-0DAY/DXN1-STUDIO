# BALATRO-ISH — a card game proves the engine is not just platformers.
# five cards fan out; A/D select, SPACE plays the selected card to your
# hand and scores it. chips + mult, no physics, pure state.
# run:  dxn3 sdk/examples/cards.py
from dxn3 import *

background("#0d1b12")
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
SUITS = ["♠", "♥", "♦", "♣"]
selected, played, chips = 0, [], 0

deck = label("title", 2, 1, "BLATRO — A/D select · SPACE play · chips: 0")
hand_lbl = label("hand", 2, 3, "hand:")
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
    for i, (c, t, rank, suit) in enumerate(cards):
        c.color = "#facc15" if i == selected else "#1f2937"
        t.y = (H // 2 - 5) if i == selected else (H // 2 - 3)

def on_key(k):
    global selected, chips
    if k == "left":  selected = (selected - 1) % len(cards)
    if k == "right": selected = (selected + 1) % len(cards)
    if k == "space":
        c, t, rank, suit = cards[selected]
        chips += 2 if suit in "♥♦" else 1
        t.text = t.text + " ✓"
        deck.text = f"BLATRO — played {rank}{suit} · chips: {chips}"
        print("played", rank + suit, "chips", chips)

def on_tick(dt2):
    redraw()

run()
