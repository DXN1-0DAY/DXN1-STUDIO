# a SHOOTER in the DXN1 STUDIO — run:  dxn3 sdk/examples/shooter.py
# v3.1.47 wears the engine's light: the muzzle GLOWS when you fire
# (and fades honestly in tick), bolts carry their own small halo, and
# every hit respawns the next threat as a GHOST — alpha 0.15 rising to
# full over DRIFT seconds, the radar-field's law, so the void always
# announces what it is about to throw at you. Even the first threat
# drifts in.
# v3.1.73 adds a SECOND THREAT CLASS — the drifting twin: smaller,
# faster, riding a sine bob, worth 25 to the bulk's 10. Both threats
# respawn from their OWN NAMED STREAMS (the seed chapter's
# one-stream-per-concern: "the threat's return", "the twin's return")
# so the same run deals the same respawns forever, and a replay probe
# can predict every position to the packet.
# v3.1.76 — NIGHT FALLS ON THE VOID: the TENTH hit turns the sky. The
# night's furniture (nine stars and a moon) is born from its OWN
# seeded stream ("the night sky" — the threat and the twin keep
# theirs), created FIRST so the world renders over it, every star a
# rumor at alpha 0.15 and the moon a whisper at 0.25 until the tenth
# hit says otherwise. Then the fade law, honest in dt: nightT climbs
# 0.75 over two seconds, the stars ride 0.15 + 0.75 * nightT, the moon
# 0.25 + 0.75 * nightT — and when the fade completes the moon SHINES
# (glow 4) and the hunters wear a faint halo of their own (the cacti
# law: glow 2, riding the same fade). The hits are counted, the night
# is said once — "night falls at ten" — and the streams never share a
# draw with the sky.
# v3.1.80 — THE OWL HUNTS THE FLASH: the void's third threat flies
# only after dark. The owl is born from its OWN seeded stream ("the
# night owl" — every other stream keeps its draws), parked off-screen
# until the night is FULL and the muzzle calls it: each shot fired at
# full night is a real event the stream may answer — one draw in
# three, and the launch takes two more (an edge to enter from, a row
# in the bolt lanes to cross). The drift announces it (alpha 0.15
# over DRIFT — the radar-field law, the void ALWAYS shows its hand),
# it wears its own halo, and it crosses dt-free at the hunter's pace
# (the twin's law). It never touches the ship — it hunts BOLTS: a
# bolt that touches the shadow dies by it, the owl leaves fed, the
# score pays nothing. Greed feeds it; holding fire starves it.
from dxn3 import *
import random, math

background("#0a0d1c")

# the NIGHT'S FURNITURE — created FIRST so the world renders over it
# (the flappy law). nine stars and a moon from their OWN seeded stream
# ("the night sky" — the threat and the twin keep theirs): every star
# a rumor at 0.15, the moon a whisper at 0.25, until the tenth hit.
NS = random.Random("the night sky")
stars = []
for i in range(9):
    st = circle(f"star{i}", NS.randint(2, W - 4), NS.randint(2, H // 3),
                1, 1, "#e2e8f0")
    st.alpha = 0.15
    stars.append(st)
moon = circle("moon", W - 15, 4, 5, 5, "#f1f5f9")
moon.alpha = 0.25
moon.glow = 0                             # the moon waits to shine

ship  = rect("ship",  W // 2 - 6, H - 12, 12, 5, "#8b5cf6"); ship.tag = "ship"
ship.glow = 0                             # declare the light before it speaks
enemy = circle("enemy", W // 3, 6, 10, 10, "#fb7185"); enemy.tag = "enemy"
enemy.alpha = 0.15                       # the first threat drifts in too
twin  = circle("twin",  W - 18, 14, 7, 7, "#38bdf8"); twin.tag = "twin"
twin.alpha = 0.15                        # the twin announces itself as well
hud   = label("hud", 2, 2, "SCORE 0")
score, shots = 0, 0
live = []                                # the bolts still in the sky
DRIFT = 0.9                              # seconds from ghost to full
TWIN_SPEED = 0.55                        # the twin drifts nearly twice as fast
TWIN_BOB = 4.0                           # the bob's amplitude, world px
twb = 14.0                               # the bob's base row
twp = 0.0                                # the bob's phase
hits = 0                                 # every kill counts toward the night
night = False                            # the tenth hit turns the sky
nightT = 0.0                             # the fade's own clock, honest in dt
TH = random.Random("the threat's return")  # one stream per concern —
TW = random.Random("the twin's return")    # each named after what it grows
OW = random.Random("the night owl")        # the owl draws only on real
                                           #   shots, never while it flies
owl = circle("owl", -999, 6, 8, 6, "#c4b5fd"); owl.tag = "owl"
owl.alpha = 0.15                         # the drift announces every flight
owl.glow = 2                             # and it wears its own halo
OWL_SPEED = 2.2                          # the hunter's pace, dt-free
owl_vx = 0.0                             # 0.0 = parked

def on_key(k):
    global shots, owl_vx
    if k == "left":  ship.x = ship.x - 1
    if k == "right": ship.x = ship.x + 1
    if k == "space":
        shots += 1
        s = circle(f"shot{shots}", ship.x + 5, ship.y - 3, 3, 3, "#facc15")
        s.vy = -2.5
        s.tag = "shot"
        s.glow = 2                       # the bolt carries its own light
        ship.glow = 5                    # the muzzle speaks — tick fades it
        live.append(s)                   # the ledger remembers its own
        if night and nightT >= 1 and owl_vx == 0.0:
            # the owl hunts the flash: each full-night shot is a real
            # event, one draw in three wakes it, and a wake takes two
            # more draws — the edge it enters from, the bolt row it
            # crosses. The stream rests while the owl flies.
            if OW.randint(1, 3) == 1:
                from_left = OW.random() < 0.5
                owl.x = -12.0 if from_left else W + 2.0
                owl.y = float(OW.randint(4, 10))
                owl_vx = OWL_SPEED if from_left else -OWL_SPEED
                owl.alpha = 0.15         # the drift announces it again

def on_tick(dt2):
    global twp, nightT, owl_vx
    enemy.x = enemy.x + 0.3
    if enemy.x > W - 12: enemy.x = 2
    if enemy.alpha < 1: enemy.alpha = min(1, enemy.alpha + dt2 / DRIFT)
    twp += dt2 * 2.2                     # the bob's phase, honest in dt
    twin.x = twin.x + TWIN_SPEED
    if twin.x > W - 9: twin.x = 2
    twin.y = twb + math.sin(twp) * TWIN_BOB
    if twin.alpha < 1: twin.alpha = min(1, twin.alpha + dt2 / DRIFT)
    if ship.glow > 0: ship.glow = max(0, ship.glow - 12 * dt2)
    if night and nightT < 1:             # the sky fades in over two seconds
        nightT = min(1, nightT + dt2 / 2)
        for st in stars:
            st.alpha = 0.15 + 0.75 * nightT
        moon.alpha = 0.25 + 0.75 * nightT
        moon.glow = 4 if nightT >= 1 else 0   # and then the moon shines
        enemy.glow = 2 * nightT          # the hunters wear the fade —
        twin.glow = 2 * nightT           # the cacti law, faintly ringing
    if owl_vx != 0.0:                    # the owl crosses, dt-free
        owl.x = owl.x + owl_vx
        if owl.alpha < 1: owl.alpha = min(1, owl.alpha + dt2 / DRIFT)
        if owl.x < -14 or owl.x > W + 14:   # it leaves hungry
            owl.x = -999
            owl_vx = 0.0
    # the bolts come home: what leaves the sky takes its light with it.
    # a shot that never dies is an entity the studio scans forever —
    # the hit-pair scan is O(n^2) over the scene, so a leak here is a
    # slow-down paid on every later frame.
    for s in live[:]:
        if s.y < -4:
            destroy(s.name)
            live.remove(s)
    hud.text = "SCORE " + str(score)

def on_hit(a, b):
    global score, twb, twp, hits, night, owl_vx
    pair = (a.tag, b.tag)
    hits += 1                                # every kill counts toward the night
    if not night and hits >= 10:
        night = True                         # the tenth hit turns the sky
        say("night falls at ten")            # said once, honestly
    if "shot" in pair and "enemy" in pair:
        shot = a if a.tag == "shot" else b
        score += 10
        destroy(shot.name)
        for s in live[:]:
            if s.name == shot.name:
                live.remove(s)           # the ledger forgets the spent bolt
        enemy.x = TH.randint(2, W - 14)  # the threat's own stream answers
        enemy.y = TH.randint(2, H // 2)
        enemy.alpha = 0.15               # the next threat fades in from the void
        print("hit! score", score)
    elif "shot" in pair and "twin" in pair:
        shot = a if a.tag == "shot" else b
        score += 25                      # the twin pays double-plus — it moves
        destroy(shot.name)
        for s in live[:]:
            if s.name == shot.name:
                live.remove(s)
        twin.x = TW.randint(2, W - 14)   # the twin's own stream, never shared
        twb = TW.randint(6, H // 2)      # the bob re-anchors at the new row
        twin.y = float(twb)
        twp = 0.0
        twin.alpha = 0.15                # and the void announces it again
        print("twin! score", score)
    elif "shot" in pair and "owl" in pair:
        shot = a if a.tag == "shot" else b
        destroy(shot.name)               # the bolt dies by the shadow
        for s in live[:]:
            if s.name == shot.name:
                live.remove(s)           # the ledger forgets it too
        owl.x = -999                     # the owl leaves, fed
        owl_vx = 0.0
        say("the owl takes your shot")   # the night's due, said plainly
        print("owl! a bolt feeds the shadow")

run()
