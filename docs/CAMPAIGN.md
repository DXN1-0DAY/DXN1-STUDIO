# The Campaign — a field guide

Five scenes, one loop: **playground → the gap → the movers → the climb →
the gauntlet → back home.** Every scene is a plain `.dxn1.json` file; the
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

## Design notes (for scene authors)

- Climb steps stay under ~90 px; anything higher rides a mover.
- Every hazard is avoidable at walking speed unless a sign promises
  otherwise — surprise spikes are bugs, not difficulty.
- Coins mark the intended line: if the magnet pulls you somewhere, that
  somewhere is the level talking.
- `next` must point at a real file — gate 3b fails the build on ghost
  doors, so broken chains cannot ship.
