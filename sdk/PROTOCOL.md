# the dxn3 wire protocol — your code, our engine

A dxn3 game is a **child process in any language**. The engine spawns it,
talks line-delimited JSON over its stdin/stdout, and renders whatever the
child describes. Your code owns the game state and the game logic; the
engine owns pixels, input, collisions, the IDE, and the console.

Nothing here is hidden: this document IS the SDK contract, and `sdk/dxn3.py`
/ `sdk/dxn3.js` are thin, readable implementations of it. Any interpreter
that can read lines and print lines can host a game.

## the handshake

```
engine → child : {"t":"hello","w":<world width px>,"h":<world height px>}
child → engine : {"t":"scene", ...full scene, see below}
engine → child : {"t":"tick","dt":<seconds>,"keys":{"left":b,"right":b,
                  "jump":b,"space":b},"chars":"<letters typed this frame>",
                  "hits":["nameA","nameB", …flat overlap pairs]}
child → engine : {"t":"frame","set":[{entity patches}],"del":["names"],
                  "vars":{"score":42},"camera":{"x":…,"y":…,"zoom":…},
                  "say":"transient HUD line","win":"banner + flash"}
child → engine : {"t":"print","m":"a line for the studio console"}
```

World coordinates: `0,0` is the top-left, `w`×`h` from the hello packet.
One world pixel ≈ one terminal cell at zoom 1.

## the scene packet

```json
{"t":"scene","name":"my game","bg":"#0b0e1a","gravity":0,"magnet":0,
 "camera":{"x":480,"y":270,"zoom":1},
 "entities":[{"name":"ship","shape":"rect","x":460,"y":480,"w":42,"h":30,
              "color":"#8b5cf6","tag":"player","vx":0,"vy":0,
              "rot":0,"spin":0,"text":"","tsize":20,"visible":1}]}
```

Shapes: `rect` · `circle` (a real disc) · `tri` (triangle) · `text`
(a plaque rendering `text`). Tags are yours — the engine reports overlap
pairs for any tagged entities; the SDK fires `on_hit` when a pair ENTERS.

## the light fields — glow, flash, alpha

Any entity may carry `"glow": <px>` — a dim halo painted behind the
body (a real ring on circles, the coins' rect aura elsewhere). Both
rasters obey, and the frame's `set` can patch it like any field, so a
pulse is just a patch per frame.

Any entity may carry `"flash": <0..1>` — a hit-flash that bleaches
the body toward white. Both rasters render it; **who decays it
depends on who owns the tick**:

| you are… | flash decay | glow decay | alpha |
|---|---|---|---|
| a `:scene` demo (the engine's own entities) | the engine's update decays it at **4/s** | never — the scene animates it | the scene animates it |
| a wire game (this protocol) | **the studio keeps what you last sent** — the decay is YOUR job | same — your job | same — your job |

That asymmetry is a law, not a footnote: a wire game that sets
`flash = 1` once and never lowers it ships a card bleached white
forever (this exact bug shipped and was fixed in v3.1.55). The
house style is an **honest staircase** — decay by a constant rate
every tick (`flash -= 3*dt`, `glow -= 8*dt`), so the light tells
the truth about its own age. A fade must also survive its birth
tick: compute the decay BEFORE the spawn, or the subject is born
already faded.

Any entity may carry `"alpha": <0..1>` (default 1) — the body blends toward the scene bg, so a scene can ship ghosts, fog banks and glass. `alpha: 0` is the bg itself; both rasters blend identically, and a wire `set` can thin or thicken it live (a vanishing act is a patch).

## the frame packet — every tick, patch the world

`set` patches entities **by name**: known names update in place, unknown
names spawn. Omitted fields keep their value. `del` retires names.
`vars.score` mirrors to the studio HUD. The SDKs expose `say(...)`
and `win(...)` for the frame's `say` and `win` fields — the words ride
ONE frame, then the run loop clears them. Anything unparsable a child prints
(a stray `print`, a traceback, a debug line) becomes a console line — the
engine never crashes because a game did.

## the hit-pair scan — who owns collision

**The child owns the DECISION, the studio owns the DETECTION.** A wire
game never checks overlaps itself. Every tick the studio walks the
scene it just rendered, collects the overlapping pairs of **tagged**
entities, and forwards them flat in the next tick packet:

```
engine → child : {"t":"tick", …, "hits":["land","pad0","bird","ptop1"]}
```

The SDK fires `on_hit(a, b)` when a pair ENTERS — once per contact, not
every tick of it. The laws that bite:

**The tag law.** Untagged entities never collide — the full-screen sky,
the hud, decoration and furniture stay out of the scan for free. Tag
only what can be touched; a tagged anything is an O(scan) anything.

**The one-frame lag law.** The pairs describe the LAST rendered frame:
tick runs before hits, and the hud a hit updates lands the NEXT frame.
Pin the consequence one frame after the packet that carried the cause.

**The enter law.** `on_hit` is edge-triggered — a bird riding a pipe
wall fires once at the touch, not every tick of the ride. If repeating
contact should keep hurting, the game re-arms it; if it should pay
once, the game guards it (lunar's `if flash > 0: return`).

**The probe law.** Because the child does no detection, a probe harness
must INJECT hits itself — `"hits": ["land", "pad0"]` reaches `on_hit`
exactly as a live overlap would. Every shipped example's probe pays
this law; a probe that waits for a real overlap waits forever.

**The cost law.** The scan is O(n²) over the scene, every frame — so a
wire game that never destroys its own projectiles leaks entities the
scan pays for forever (shooter's bolts did exactly this, fixed in
v3.1.63). What leaves the stage takes its light with it: destroy it,
and forget it in the same tick.

## the seed chapter — determinism for game authors

A seeded game replays itself: the same run grows the same desert, the
same ghosts, the same owl. The recipe the shipped examples share:

**FNV-1a of the game's name, xorshift after.** Seed with FNV-1a over a
short name (`"the long run"`), then draw with xorshift:

```
s ^= s << 13;  s ^= s >>> 17;  s ^= s << 5;   // then s / 2^32
```

**The JS signed-int32 law — the one that bites.** JavaScript's bitwise
ops yield SIGNED int32: once bit 31 sets, the seed multiplies as a
NEGATIVE double and `ToUint32` wraps that. The unsigned FNV everyone
writes in python NEVER matches it. Mirror the sign:

```
h ^= ord(ch)
if h >= 1 << 31: h -= 1 << 32
h = int(float(h) * 16777619) % (1 << 32)
```

**One stream per concern.** The desert's seed stays dedicated — the
sky seeds `"the night sky"`, the owl seeds `"the night owl"`. A stream
that shares draws with a neighbor makes every neighbor's future depend
on it. Name the stream after what it grows.

**Draw only on the event.** A spawn interval is drawn at the moment of
the spawn, never while waiting at the door — waiting consumes no
randomness, so a blocked gate cannot shift the stream. A probe that
replays the stream can then predict every event to the packet, with
zero drift.

**Reseed on rebirth, continue across lives.** `walkAgain` reseeds the
streams that name the RUN (the owl's) and lets continue the streams
that name the WORLD (the desert's). Pick per stream, and write the
choice down — the probe replays exactly what the game decided.

## the replay probe — proving a seeded game's law

A seeded game does not have to be PLAYED to be believed — it can be
PROVEN. A replay probe drives the real child over the real wire and
pins the packets: the say on the clear's own frame, the banner's
birth bloom, the wear staircase. The sprint's worked example: the
tetris streak ×2, hunted from the EMPTY well — 90 scripted events,
clears at locks 14/15/18 (runs 1, 2, 1), twelve pins green. The laws
the hunt paid for:

**One event = one tick.** A probe script is a list of events, each
sent as its own tick: the key held for exactly that frame. The held
grammar carries `left`, `right`, `jump`, `space`; letters ride
`chars` (`r`, `c`, `s`). A turn is `jump` — the wire's held keys
never carried "up".

**The float timeline law — the one that bites twice.** The game's
gravity accumulates `dropT += 0.05` and fires at `>= 0.5` — but ten
float additions read `0.4999999999999999`, never `0.5`. The real
cadence is a fire every 11 ticks at dt 0.05, and a sim that models
ten fires per half second drifts a full row every piece. Accumulate
the float EXACTLY like the game — the same law that bit the seed
(signed int32) bites the clock.

**The unswept spawn law.** The game's `lock()` calls `spawn()` BEFORE
the sweep — the top-out check reads the UNSWEPT well, the full row
still in place, one row taller. A sim that sweeps first is wrong by
a row at every clear, and will call alive what the game calls dead.

**The script search.** To find a script that proves a law, beam over
tick-exact placements — every (turns, slides, slam) sequence run on
the sim, deduped by resulting state — scored by construction
(fullness, hole-subset alignment, the open head). Collect every
combo-live state, scan the next piece exhaustively for the back-to-
back clear, then beam the dry locks and the isolated clear that
proves the reset. The probe pins the say on the very frame the sim
says it is born — sim and wire agree to the tick, or the pin goes
red and the law is not done.

## driving a live game — the probe's eight laws

The replay pins a script; a LIVE driver plays the game — steering,
hunting, spending. Five rounds of dark-of-night failures minted the
laws (the snake heat probe paid for most of them):

**1. The coast law — keys land after the tick.** The SDK runs a
packet's tick handlers FIRST and its keys AFTER, so a turn sent in
packet N first applies at packet N+2: the head (the ship, the
lander) ALWAYS coasts one cell of inertia before any turn can land.
Judge every safety from the coast cell — head + one cell of the
current facing — never from the head itself.

**2. wasd rides `chars`.** The `keys` dict dispatches only `left`,
`right`, `jump`, `space` — `w`, `a`, `s`, `d` and every other
keystroke ride the `chars` string. A probe that puts `"s"` in the
keys dict steers NOTHING, silently. And the fine print the chase
probe bled for: `chars` dispatches PER CHARACTER — `"right"` as
chars arrives as r, i, g, h, t, five wrong keystrokes. Single
letters ride chars; multi-char names ride the keys dict or nothing.

**3. A turn pair rides `chars` alone.** The keys dict dispatches in
its own fixed order (`left, right, jump, space`) and the chars
string dispatches after — mixing both reverses an ordered pair.
When order matters, put the whole sequence in `chars`: the string's
order IS the queue's order.

**4. The probe is the metronome.** Send dt = the game's own speed
law (the same expression, the same double) and every packet is
exactly one step — no phase drift, no double steps, no fantasy
steering. The float-timeline law above is this law's sibling:
accumulate the game's clocks with the game's own arithmetic.

**5. Deterministic coverage beats any greedy hunter.** A greedy
chaser orbits its food (the no-reverse law plus one packet of coast
makes the food a blind spot); pockets, lookaheads and intercept
leads each fail in some regime. A serpentine that visits every cell
crosses whatever cell the food occupies, and its self-safety is a
theorem, not a hope: parallel corridors one row apart, the trail
farther behind than the snake is long.

**6. Console.log rides the pipe bare.** A wire child's `print` /
`console.log` arrives on stdout as NON-JSON lines between the
packets. A reader that treats a non-JSON line as a stall will hang
on the first say; read past the chatter, time out on silence only.

**7. The arrival body is not the present body.** A decision lands
two packets after it was made — the tail-end cells of a snake's body
will have vacated by then, mid-chain cells will have advanced. Pin
occupancy against the body the head will MEET, or the probe hunts
its own phantom.

**8. A command flies one tick — aim from the post-tick cell.** The
turn a probe sends in packet N is enqueued after packet N's step and
applies at packet N+1's step. A driver that aims from the cell the
head just left takes every corner one step late — the chase probe
sailed its snake through every turn and into the wall it meant to
avoid, all while every pin checked green against its own lagging
plan. Aim from the post-tick cell (or verify the head landed where
the last command pointed before choosing the next one), and let dt
carry exactly one step per packet so the flight stays predictable.

## hosting any language

The engine picks a runner by extension, honestly:

| file | runner |
|---|---|
| `.py` | `python3 file` (PYTHONPATH includes `sdk/` — `from dxn3 import *`) |
| `.js` `.mjs` | `node file` (NODE_PATH includes `sdk/` — `require('dxn3')`) |
| `.cpp` `.cc` `.cxx` | `g++ -std=c++23 -O2` → run the binary |
| `.cs` | `dotnet script file` |
| anything else | `--host-cmd 'ruby game.rb'` — any interpreter you have |

No runner? The error says so, by name — nothing pretends.

## the studio around it

`dxn3` with no arguments opens the IDE: an editor pane, a live viewport,
and a console rail. Type code, pause — the game refreshes itself
("code a background and boom, a background"). `ctrl+r` runs, `ctrl+s`
saves, `esc` plays fullscreen, `e` returns to the editor, `:scene`
loads a demo, `:q` quits.

## the wire's words — the host's lifecycle, confessed

The studio's event wire (`DXN3_TRACE=<path>`) is where the machine
keeps its diary: one line per receipt, `EVENT <word>`. The host's own
lifecycle speaks it now, in kind with the shell's vocabulary (see
`docs/ARCHITECTURE.md` for the wire's full dictionary and its laws):

| Word | Spoken when | Receipts (the pins) |
|------|-------------|---------------------|
| `wire: hosting <cmd>` | the studio spawned your game (the runner + your file) | sdk_wire_probe (gate 8 — the real wire, the real child) |
| `wire: built N entities` | your scene packet became the stage | sdk_wire_probe (N agrees with the rail's count — one truth, two mouths) |
| `wire: host exited (code N)` | your process returned or died, code and all | sdk_wire_probe (the child slain mid-run; the code is yours) |

The laws ride along: the lifecycle words ride the **direct line** (the
host spawns before the loop, so a parked event would die in the old
`Game`'s slot — the writer lives above the spawner); and your
`print()` lines **never** masquerade on the wire — the console rail is
their only mouth (the refusals' law: a silence the probes pin is law,
not omission). Gate 6 (`scripts/sdk_conformance.py`) pins your scene
and frames from a fake engine; gate 8's `sdk_wire_probe.py` pins the
studio's side from the real one.
