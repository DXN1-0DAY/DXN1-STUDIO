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

## the frame packet — every tick, patch the world

`set` patches entities **by name**: known names update in place, unknown
names spawn. Omitted fields keep their value. `del` retires names.
`vars.score` mirrors to the studio HUD. The SDKs expose `say(...)`
and `win(...)` for the frame's `say` and `win` fields — the words ride
ONE frame, then the run loop clears them. Anything unparsable a child prints
(a stray `print`, a traceback, a debug line) becomes a console line — the
engine never crashes because a game did.

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
