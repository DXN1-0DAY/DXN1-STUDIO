# The Campaign — a field guide

Ten scenes, one loop: **playground → the gap → the movers → the climb →
the gauntlet → the vault → the ascent → the descent → the beacon →
the crossing → back home.** Every scene is a plain
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

## Design notes (for scene authors)

- Climb steps stay under ~90 px; anything higher rides a mover.
- Every hazard is avoidable at walking speed unless a sign promises
  otherwise — surprise spikes are bugs, not difficulty.
- Coins mark the intended line: if the magnet pulls you somewhere, that
  somewhere is the level talking.
- `next` must point at a real file — gate 3b fails the build on ghost
  doors, so broken chains cannot ship.
