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
