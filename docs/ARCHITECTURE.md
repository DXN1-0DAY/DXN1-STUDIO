# DXN1 STUDIO 3 — architecture

    ┌───────────────────────────── Electron ─────────────────────────────┐
    │  renderer/  (the FACE — beautiful, replaceable)                    │
    │    index.html · styles.css · app.js (IDE brain) · spark.js (2D)    │
    │        │  window.dxn1.request(cmd, args)  — contextIsolated        │
    │    main.js  spawn engine · frame ids · 30 s timeouts · win IPC     │
    └──────────────────────────────┬─────────────────────────────────────┘
                                   │ stdio, one JSON object per line
    ┌──────────────────────────────▼─────────────────────────────────────┐
    │  engine/  (the BRAIN — Python)                                     │
    │    {"id":N,"cmd":"read","args":{"path":"a.py"}}                    │
    │    →  {"id":N,"ok":true,"result":{...}}  |  {"ok":false,"error":…} │
    │    commands: hello tree read write mkdir rename delete stat        │
    │              scene_get scene_save                                  │
    └────────────────────────────────────────────────────────────────────┘

## Rules the rebuild keeps (they were earned in DS2)

1. **The engine never crashes the face.** `handle()` never raises; bad
   lines get honest error replies. The face survives a dead engine in
   demo mode (virtual FS, labelled honestly in the statusbar).
2. **Paths are sandboxed.** Every resolve refuses to escape the
   workspace. Writes are atomic (tmp + rename).
3. **Every control works.** No dead buttons — if the engine is absent
   the same buttons act on the demo filesystem.
4. **Scenes are data.** `*.dxn1.json` — the editor writes what the
   engine runs. No private formats.
5. **No build step.** Plain HTML/CSS/JS + Python. `node --check` and
   `python3 -m compileall` are the gates; unittest covers the engine.

## Version scheme (set by DXN1)

`VERSION` file is canonical for display: **v3.0.01**, v3.0.02, …
`package.json` carries the semver-nearest value (3.0.1). One giant
update per hour while the sprint runs.
