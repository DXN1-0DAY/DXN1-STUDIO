# The Campaign — a field guide

Thirteen scenes, one loop: **playground → the gap → the movers → the climb →
the gauntlet → the vault → the ascent → the descent → the beacon →
the crossing → the fog → the return → the epilogue → back home.** Every scene is a plain
`.dxn1.json` file; the
goal door carries you to the next, and the last door brings you home. The
HUD counts `COINS x/y · SCORE · TIME` the whole way — completionists grab
every coin before touching a door.

## playground — where the studio teaches

The tutorial that plays like a demo. Three ledges stair up to the right, a
bouncer and a bouncing ball share the yard, two fangs punish careless
walking, and a sign does the onboarding: *find the coins*. The door sits at
the far right; the ledge work above it is optional practice for what the
campaign will ask of you. Everything the later levels use — movers,
magnetized coins, respawning fangs — is here in miniature.

## level-1 — the gap

The first honest test. A wide pit with fangs at the bottom splits the
world; a horizontal mover ferries you across if you read the sign (*ride
the mover*) and time the hop. On the far side a watcher guards the path
and an elevator lifts you to the sky ledge where the exit waits. Five gems
total: two behind you at the start, one over the pit, one past the
watcher, one in the sky.

## level-2 — the movers

Movers graduate from ferry to lifestyle. Two diagonal platforms on
staggered heights carry you over the pit — the first to a high line, the
second along the ridge — while a spinning saw patrols the ground between
and a fang guards the landing. The sign (*ride the movers!*) is both hint
and warning: standing still on a moving platform is a skill, and the coins
hang exactly where the ferries peak.

## level-3 — the climb

The studio goes vertical. From the yard, a springboard offers a greedy
shortcut toward the first ledge (the honest route is the stair on the
right); then lift-1 carries you a full screen of height to ledge-b, where
a watcher guards the walk to lift-2. The second lift deposits you on the
summit — the only gradient-painted ground in the campaign, because the top
of the world should look like something. Four gems on the way up, one on
the roof.

## level-4 — the gauntlet

The exam. Nine fangs line the pit floor; three ferries cross it on
staggered heights (low, high, diagonal), and the saw-guarded island in the
middle is the only rest stop — its saw spins in place, so the safe lane
shifts with every rotation. The far ledge hides a second saw above the
final stretch: run under it, don't jump. Five gems, the meanest jump
timing in the campaign, and a last door that brings you home to the
playground — where the ball is still bouncing.

## level-5 — the vault

The vault opens after the gauntlet's last door and it is MACHINES: two
counter-phased lifts trade the first pit between them (ride one up as the
other comes down), a saw patrols the high deck's airspace, and the drop
ledge's single fang punishes the lazy landing. The ferry under the second
saw asks for a crouch-run's patience — wait half a rotation, then cross.
The isle is honest ground; the last stretch is not: two fangs, one gap,
and the door home. Five gems, one per machine, none free.

## level-6 — the ascent

The tower the vault was quietly rehearsing you for. Three lifts stack the
climb — the first a slow ride out of the yard, the second counter-phased
against the terrace you leave, the third the longest pull — and between
them, five terraces of honest ledge work. The saws finally bite here (the
engine learned the hazard tag the hard way: six scenes of decorative saws
before this one): saw-1 guards terrace-2's airspace at jump height, saw-2
sits on the mid-deck like a toll. Both clear with a running jump; both
punish a lazy one. Six gems — two over the first terrace, one on the deck,
one on the sky ledge, two on the summit — and the campaign's highest door,
painted indigo because the top of THIS world earned it.

## level-7 — the descent

The summit's answer: the only way out is DOWN. The campaign's first
vertical drop — five platforms stair-stepping from the clouds to a
vault floor painted the same indigo the ascent earned — and the
first home of the LEANING FANGS: spikes with a rot of their own
(20°, 30°, 40°, two of them leaning against the grain), possible
since the engine learned to turn (v3.1.10) but never used until
now. The saws spin where they always spun — you can finally SEE
it — with carousel-saw running 360°/s as the fastest thing in the
campaign. Three lifts, all headed down or counter-phased; six
gems marking the honest line; and a door that dumps you back in
the playground, where every run begins.

## level-8 — the beacon

v3.1.20 taught every entity to glow; the beacon is the first scene BUILT
from that law. The wayfinding is literally made of light: six gems and
the goal door itself all carry `"glow": 7`, strung across the darkest
sky in the campaign (#070912) — follow the bright line and you cannot
get lost. The platforming keeps the descent's lessons honest: a fang
leaning against the grain at the very first step, two saws spinning at
300°/s and 340°/s over the mid-deck, and the closing pull rides two
counter-phased lifts plus a summit ferry. Six gems, one lit door, one
ride home to the playground.

## level-9 — the crossing

After the beacon's light, the campaign asks you to TRUST it: three
abysses with no floor at all, crossed only by ferries that keep a
timetable (75, 85 and 90 px/s — each rung of the crossing a little
faster than the last). The middle abyss offers the campaign's honest
dilemma: a HIGH road over two pillars where the gems glow and a fang
leans across the exit, or the LOW ledges where the way is longer but
nothing leans. Two saws keep the decks (300°/s and 340°/s), the last
pull is a vertical ferry to a summit that pays two gems for the climb,
and the door home waits at the top of the far shore. Seven gems —
four of them lit — one timetable, no shortcuts.

## level-10 — the fog

The crossing taught you to trust the ferries; the fog asks you to
trust the AIR. Four platforms in this scene are made of mist
(`"alpha": 0.35`–`0.5` — v3.1.28's law, used as terrain): you can
SEE THROUGH them, and they hold you anyway. The sign at the gate
says the only true thing about this place — what you can see through
is still real. Between the mist sits honest ground with teeth: two
saws (280°/s, 320°/s), a fang leaning against the grain, and a ferry
across the one gap the fog refuses to bridge. Four of the seven gems
float over mist — every one of them glowing, so the light marks what
matters even when the ground won't. One lift, one lit door, one ride
home through the fog you came from.

## level-11 — the return

The finale is a homecoming built from every law the road taught. The sky
lifts a shade (#0d1220 — dawn thinks about it), and then the callbacks
walk beside you one last time: the FOG's mist carries three ledges (what
you can see through is still real), the CROSSING's ferry keeps its
timetable (85 px/s) over the one gap nothing bridges, the VAULT's two
lifts trade the deep pit counter-phased — path one rides up while path
two falls, and the top-to-top hop between them is the campaign's last
honest breath-hold — and the GAUNTLET's saws keep their tolls above the
decks at 300 and 320°/s, with a leaning fang for old times' sake. The
last stretch is a beacon-style stair of three small decks, every other
gem glowing, and the door itself wears `"glow": 7` — the same light that
guided you through the beacon now marks home. Eight gems, the
campaign's best pay, and a door that lands you past the credits — in
the epilogue, where the road says goodbye properly.

## level-12 — the epilogue

The thirteenth scene is not a test — it is a thanks. The sky drops to
the quiet hour (#0b1020, darker than the fog ever asked you to read),
and then the campaign replays itself at walking pace, one law at a
time, nothing stacked: two mist ledges open the walk (the FOG's
*what you can see through is still real*, one last time), a slower
ferry crosses the honest gap (75 px/s — the CROSSING's timetable with
nowhere to be), one saw keeps its 280°/s toll above the east dock, and
the VAULT's two lifts ride you up to the high deck where a leaning fang
waits for old times' sake. The way down is mist again, then the
BEACON's stair of three decks carries every other gem glowing to the
summit — where the farewell sign (*thank you for playing — the door is
home*) stands beside the door itself: glow 9, the brightest light the
campaign has ever shipped, outshining the beacon's 7 because an ending
deserves to be seen. Eight gems again, the door drops you in the
playground, the ball is still bouncing, and the loop closes where it
began — the epilogue's quiet last word before the road starts over.

## Design notes (for scene authors)

- Climb steps stay under ~90 px; anything higher rides a mover.
- Every hazard is avoidable at walking speed unless a sign promises
  otherwise — surprise spikes are bugs, not difficulty.
- Coins mark the intended line: if the magnet pulls you somewhere, that
  somewhere is the level talking.
- `next` must point at a real file — gate 3b fails the build on ghost
  doors, so broken chains cannot ship.

## The grand tour — the campaign walked on the wire

The chain walk (gate 8) proved one hop: a hero walked through the
playground's door and the shell consumed `pendingNext` into level-1,
with the load spoken on the event wire where machines read it. The
grand tour (probes/grand_tour_probe.py, gate 8 since v3.1.115) is the
sequel: keep walking — it pins THREE receipts (level-1, level-2,
level-3) in ~50-55s and has retired campaign_walk.py, whose ungated
five-minute stall was a live trap the family tree had to name.
The walker is a state machine with laws, not a script — run, board,
listen, ride — and every law it learns comes from a scene the tour
had to cross:

- **Boarding is arithmetic, not rhythm.** The walker simulates the
  ferry's ping-pong and jumps only when the predicted landing
  (x + range, flight seconds from now) will be well inside the
  ferry's span. Hand-tuned phase windows died because the flight time
  was a lie: the ferry moves half its width while the arc flies, and
  a landing one pixel short is a fang pit. The margin is asymmetric
  on purpose.
- **Listen after every landing.** If the ground carries you (position
  moves with no input across a 0.3s window — per-poll thresholds read
  a 55 px/s lift as "still"), the ride law takes over: ferries watch
  their exit windows, lifts ride to their TOP REVERSAL and leave
  walk-or-jump per the plan.
- **A tagless entity is a wall.** Level-2's sign (90-300, y 360-390)
  has no tag, and the loader hears only tags for hazards, goals,
  movers, coins and the player — everything tagless is solid. It
  wedged the blind hopper at the spawn until the deep-stuck law
  landed: after eight wedges, hold right through the whole flight.
- **Every dialect a scene can speak must be checkable.** The recon
  convicted level-2's dict-dialect paths (a documented v3.0.03 form
  the loader no longer hears — both ferries stood frozen mid-river
  with "ride the movers!" signed above a stone). Gate 3c now fails
  any scene that speaks a path the engine cannot hear; gate 3d fails
  any scene without exactly one spawn or a door where it promised a
  chain.

The tour's road: playground → level-1 → level-2 walk green three
runs straight; level-3's lifts have walked once; the full loop
(level-3 through level-12 and home) is the next rounds' walk, one
deterministic ride at a time. `DXN3_TOUR_HOPS` sets how far the tour
goes; `DXN3_TOUR_DEBUG=1` speaks heartbeats.
