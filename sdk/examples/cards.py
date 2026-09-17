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
# v3.1.74 makes the DECK real: forty cards shuffled by their OWN named
# stream ("the deck's order"), dealt five at a hand; the last play of
# a hand deals the next five and the muck grows; when the deck runs
# dry the muck RETURNS and the reshuffle stream ("the deck's
# reshuffle") reorders it — the title SPEAKS the reshuffle and the
# fresh hand ghosts in again, the radar-field law re-run.
# v3.1.80 adds the deck's LOW LIGHT: the hand label wears the
# countdown as the deck drains — quiet above ten cards, a faint ring
# at ten, and the last hand (five) burns brighter — because the
# muck's return is coming and a player deserves to see it coming
# from across the table.
# run:  dxn3 sdk/examples/cards.py
from dxn3 import *
import random

background("#0d1b12")
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
SUITS = ["♠", "♥", "♦", "♣"]
selected, played, chips, mult = 0, [], 0, 1
ghostT = 0.0                                         # the hand arrives as ghosts
spent = [False] * 5                                  # the hand remembers seat by seat
muck = []                                            # the played cards, returned on the reshuffle

deck_cards = [(r, s) for s in SUITS for r in RANKS]  # forty honest cards
RD = random.Random("the deck's order")               # one stream per concern —
RS = random.Random("the deck's reshuffle")           # each named after what it grows
RD.shuffle(deck_cards)
reshuffled = False                                   # the say rides the next title

deck = label("title", 2, 1, "BLATRO — A/D select · SPACE play · score: 0 x 1")
hand_lbl = label("hand", 2, 3, "muck: 0 · deck: 40")
cards = []

for i in range(5):                                   # the seats (ranks come from the deck)
    x = W // 2 - 24 + i * 10
    c = rect(f"card{i}", x, H // 2 - 4, 9, 7, "#1f2937")
    t = label(f"ct{i}", x + 1, H // 2 - 3, "?", "#e9e5ff")
    cards.append((c, t, "?", "?"))

def redraw():
    A = 0.15 + 0.85 * ghostT                         # the radar-field law
    for i, (c, t, rank, suit) in enumerate(cards):
        c.color = "#facc15" if i == selected else "#1f2937"
        c.glow = 6 if i == selected else 0            # the glow hand
        t.y = (H // 2 - 5) if i == selected else (H // 2 - 3)
        c.alpha = 0.5 if spent[i] else A              # the hand remembers
        t.alpha = c.alpha                             # the rank wears it too

def decklight():                         # the deck's low light — the
    """hand label wears the countdown: quiet above ten, a faint ring
    when the deck thins to ten, and the end (five or the last dregs)
    burns brighter — the muck's return is at hand."""
    n = len(deck_cards)
    hand_lbl.glow = 2 if n <= 5 else (1 if n <= 10 else 0)

def deal():
    """five from the deck; a dry deck returns the muck, reshuffled by
    its own stream, and the say speaks"""
    global played, spent, ghostT, reshuffled, selected
    if len(deck_cards) < 5:
        deck_cards.extend(muck)
        muck.clear()
        RS.shuffle(deck_cards)
        reshuffled = True                            # the exhaustion law speaks
    played = []
    spent = [False] * 5
    selected = 0
    for i in range(5):
        r, s = deck_cards.pop(0)
        c, t, _, _ = cards[i]
        cards[i] = (c, t, r, s)
        t.text = r + s
        t.color = "#facc15" if s in "♥♦" else "#e9e5ff"
    ghostT = 0.0                                     # the fresh hand ghosts in
    redraw()                                         # the birth frame is honest:
                                                     # on_key runs AFTER on_tick,
                                                     # so the deal paints itself
    decklight()                                      # the low light rides the deal
    hand_lbl.text = f"muck: {len(muck)} · deck: {len(deck_cards)}"
    print("dealt", len(deck_cards), "left in the deck")

deal()                                               # the first hand is the stream's first five

def on_key(k):
    global selected, chips, mult, reshuffled
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
        muck.append((rank, suit))                     # the muck grows —
                                                     #   real cards, not strings:
                                                     #   a returned "10" must
                                                     #   unpack as (rank, suit)
        spent[selected] = True
        if all(spent):                                # the hand is spent —
            deal()                                    # the deck answers
        hand_lbl.text = f"muck: {len(muck)} · deck: {len(deck_cards)}"
        say = " · reshuffled" if reshuffled else ""
        deck.text = (f"BLATRO — played {rank}{suit}{say} · "
                     f"score: {chips} x {mult} · deck {len(deck_cards)}")
        reshuffled = False                            # the say is born once
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
