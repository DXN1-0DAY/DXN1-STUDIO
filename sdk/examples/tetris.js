// TETRIS in the DXN1 STUDIO — the falling order, on the engine's wire.
// run:  dxn3 sdk/examples/tetris.js
// left/right move · up (or jump) rotates · s soft-drops · space
// slams · the GHOST wears alpha 0.32 where the order will land (the
// engine's alpha law as honest wayfinding) · the locked cells LIVE
// as entities (one rect per seat, named by its place) and a cleared
// line is ten honest destroys · the bag is SEEDED: the same run, the
// same falls, forever · the NEXT piece is previewed right of the well
// — the queue ahead, peeked honestly (one draw per piece, never
// re-rolled, so the seeded law survives the preview) · and since the
// VAULT: c holds the falling piece — once per drop, honestly spent
// (the vault itself wears the ghost's alpha 0.32 while it rests) and
// the swap never touches the seed's queue (the first hold consumes
// the peeked next, exactly as a spawn would).  (soft-drop rides the
// LETTER s: the wire's held keys are left/right/jump/space — "down"
// never rides it; the ghost probe exposed that latent bug.)
// THE WELL LEARNED THE LIGHT LAWS: every locked cell is born with a
// bloom of glow 2 that wears at the house's honest 3/s (decayed by
// the game itself — the studio keeps the last light a wire game
// sent, so a light the game never decays is a light FOREVER), and a
// cleared line SPEAKS twice: the transient say (the say law, 1.6 s
// of HUD) and a banner label over the well that is born whole and
// wears linearly to invisible in the same 1.6 s — never a
// flash-forever fixture. The decay runs even when the world waits
// on game over; birth shows whole because decay runs FIRST.
const dxn3 = require("dxn3");
const { rect, label, destroy, find, background, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#0a0c16");

const hud = label("hud", 2, 1, "TETRIS  ·  arrows move · up turns · s sinks · space slams · c holds · ghost marks home · 0");
const banner = label("banner", 3, 16, "", "#fde047");   // the well speaks:
banner.visible = 0;                                      // born dark, lit
let bannerT = 0;                                         // only by a clear

const COLS = 10, ROWS = 16, CELL = 2;    // the well: 10 wide, 16 deep
const BX = 2, BY = 2;                    // the well's top-left corner
rect("rail-l", BX - 1, BY - 1, 1, ROWS * CELL + 2, "#4c1d95");
rect("rail-r", BX + COLS * CELL, BY - 1, 1, ROWS * CELL + 2, "#4c1d95");
rect("floor", BX - 1, BY + ROWS * CELL, COLS * CELL + 2, 1, "#4c1d95");

const SHAPES = {                        // cells as [col,row] in the piece's box
  I: { size: 4, cells: [[0,1],[1,1],[2,1],[3,1]], color: "#22d3ee" },
  O: { size: 2, cells: [[0,0],[1,0],[0,1],[1,1]], color: "#facc15" },
  T: { size: 3, cells: [[1,0],[0,1],[1,1],[2,1]], color: "#a78bfa" },
  S: { size: 3, cells: [[1,0],[2,0],[0,1],[1,1]], color: "#34d399" },
  Z: { size: 3, cells: [[0,0],[1,0],[1,1],[2,1]], color: "#fb7185" },
  J: { size: 3, cells: [[0,0],[0,1],[1,1],[2,1]], color: "#60a5fa" },
  L: { size: 3, cells: [[2,0],[0,1],[1,1],[2,1]], color: "#fb923c" },
};
const NAMES = Object.keys(SHAPES);

// the seed: the studio's law — the same run, the same falls
let seed = 2166136261 >>> 0;
for (const ch of "the falling order") {
  seed ^= ch.charCodeAt(0);
  seed = (seed * 16777619) >>> 0;
}
const next = () => {
  seed ^= seed << 13; seed >>>= 0;
  seed ^= seed >>> 17;
  seed ^= seed << 5;  seed >>>= 0;
  return seed / 4294967296;
};

const well = new Map();                  // "row_col" -> entity name
const piece = [];                        // the four falling seats
const ghost = [];                        // the four ghost seats (alpha 0.32)
const pvue = [];                         // the four preview seats (the queue)
const hv = [];                           // the four vault seats (the hold)
let cur = "T", rotN = 0, px = 4, py = -1, cells = [], nxt = null;
let bag = [], dropT = 0, drop = 0.5, total = 0, level = 1, over = false, seq = 0;
let held = null, holdUsed = false;       // the vault and its one-per-drop law
const glows = new Map();                 // cell name -> remaining bloom

const key = (r, c) => r + "_" + c;
const free = (r, c) =>
  c >= 0 && c < COLS && r < ROWS && (r < 0 || !well.has(key(r, c)));

function pull() {                        // the 7-bag: every piece once a round
  if (!bag.length) bag = NAMES.slice();
  const i = Math.floor(next() * bag.length) % bag.length;
  return bag.splice(i, 1)[0];
}

function shapeCells() {                  // [row,col] seats after rotN turns
  const s = SHAPES[cur];
  return s.cells.map(([x, y]) => {
    for (let t = 0; t < rotN; ++t) { const tx = x; x = y; y = s.size - 1 - tx; }
    return [y, x];
  });
}

function fits(seats) {
  return seats.every(([r, c]) => free(py + r, px + c));
}

function fitsAt(dr, dc) {                // the order's seats, probed at an offset
  return cells.every(([r, c]) => free(py + dr + r, px + dc + c));
}

function ghostDrop() {                   // how far the order can still fall
  let gy = 0;
  while (fitsAt(gy + 1, 0)) gy += 1;
  return gy;
}

function paint() {                       // the falling order wears its seats
  piece.forEach((e, i) => {
    const [r, c] = cells[i];
    e.x = BX + (px + c) * CELL;
    e.y = BY + (py + r) * CELL;
    e.visible = py + r >= 0 ? 1 : 0;
  });
  const gy = py + ghostDrop();           // the ghost marks the landing
  ghost.forEach((e, i) => {
    const [r, c] = cells[i];
    e.x = BX + (px + c) * CELL;
    e.y = BY + (gy + r) * CELL;
    e.visible = gy + r >= 0 && gy !== py ? 1 : 0;
    e.color = SHAPES[cur].color;
    e.alpha = 0.32;
  });
}

const PX = 25, PY = 3;                   // the preview box (right of the well)
const HX = 25, HY = 15;                  // the vault sits under the queue

function paintPreview() {                // the queue ahead, worn in advance
  const s = SHAPES[nxt];
  const ox = PX + ((4 - s.size) >> 1), oy = PY + ((4 - s.size) >> 1);
  pvue.forEach((e, i) => {
    const [c, r] = s.cells[i];
    e.x = ox + c * CELL;
    e.y = oy + r * CELL;
    e.color = s.color;
    e.visible = over ? 0 : 1;
  });
}

function paintBanner() {                 // born whole, worn linearly:
  const a = Math.max(0, Math.min(1, bannerT / 1.6));   // 1.6 s, the say's
  banner.alpha = Math.round(a * 1000) / 1000;         // own dwell, worn
  banner.visible = bannerT > 0 ? 1 : 0;               // to invisible
}

function showBanner(msg) {               // a clear lights the well's voice
  banner.text = msg;
  bannerT = 1.6;
  banner.glow = 2;                       // the bloom wears 3/s below
  paintBanner();
}

function paintHold() {                   // the vault, worn honestly
  if (held === null) {
    hv.forEach((e) => { e.visible = 0; });
    return;
  }
  const s = SHAPES[held];
  const ox = HX + ((4 - s.size) >> 1), oy = HY + ((4 - s.size) >> 1);
  hv.forEach((e, i) => {
    const [c, r] = s.cells[i];
    e.x = ox + c * CELL;
    e.y = oy + r * CELL;
    e.color = s.color;
    e.alpha = holdUsed ? 0.32 : 1;       // a spent vault wears the ghost's
    e.visible = over ? 0 : 1;            // alpha — spent, but readable
  });
}

function spawn() {
  cur = nxt === null ? pull() : nxt;     // the queue: one draw per piece,
  nxt = pull();                          // peeked honestly, never re-rolled
  rotN = 0;
  px = COLS >> 1;
  py = -1;
  cells = shapeCells();
  piece.forEach((e) => { e.color = SHAPES[cur].color; });
  if (!fits(cells)) {
    over = true;
    piece.forEach((e) => { e.visible = 0; });
    ghost.forEach((e) => { e.visible = 0; });
    pvue.forEach((e) => { e.visible = 0; });
    hv.forEach((e) => { e.visible = 0; });
    win(`TOPPED OUT at ${total} — r falls again`);
    return;
  }
  paint();
  paintPreview();
  paintHold();
}

function holdSwap() {
  if (holdUsed) {
    say("the vault already gave — one hold per drop");
    return;
  }
  const stash = cur;
  if (held === null) {
    held = stash;
    cur = nxt;                           // the queue's peek becomes the order —
    nxt = pull();                        // one draw, the same law as a spawn
  } else {
    cur = held;                          // a straight swap: the vault gives back
    held = stash;
  }
  rotN = 0;
  px = COLS >> 1;
  py = -1;
  cells = shapeCells();
  piece.forEach((e) => { e.color = SHAPES[cur].color; });
  holdUsed = true;
  if (!fits(cells)) {
    over = true;
    piece.forEach((e) => { e.visible = 0; });
    ghost.forEach((e) => { e.visible = 0; });
    pvue.forEach((e) => { e.visible = 0; });
    hv.forEach((e) => { e.visible = 0; });
    win(`TOPPED OUT at ${total} — r falls again`);
    return;
  }
  paint();
  paintPreview();
  paintHold();
}

function lock() {
  // every locked cell becomes ITS OWN entity (named by sequence) — the
  // falling seats must stay free for the next order, or a sweep would
  // destroy the piece that is falling
  cells.forEach(([r, c], i) => {
    if (py + r < 0) return;
    const nm = `cell${seq}`;
    seq += 1;
    const e = rect(nm, BX + (px + c) * CELL, BY + (py + r) * CELL, CELL,
                   CELL, SHAPES[cur].color);
    e.glow = 2;                          // a fresh lock BLOOMS — worn by
    glows.set(nm, 2);                    // the tick's own 3/s staircase
    well.set(key(py + r, px + c), nm);
  });
  holdUsed = false;                      // a new drop re-arms the vault
  paintHold();
  spawn();
}

function sweep() {                       // the law of full rows
  let cleared = 0;
  for (let r = ROWS - 1; r >= 0; --r) {
    let full = true;
    for (let c = 0; c < COLS; ++c)
      if (!well.has(key(r, c))) { full = false; break; }
    if (!full) continue;
    cleared += 1;
    for (let c = 0; c < COLS; ++c) {     // ten honest destroys
      const nm = well.get(key(r, c));
      glows.delete(nm);                  // a destroyed cell takes its
      destroy(nm);                       // bloom off the ledger too
      well.delete(key(r, c));
    }
    for (let rr = r - 1; rr >= 0; --rr)  // everything above falls one row
      for (let c = 0; c < COLS; ++c) {
        const k = key(rr, c), kk = key(rr + 1, c);
        if (well.has(k)) {
          const nm = well.get(k);
          well.delete(k);
          well.set(kk, nm);
          const e = find(nm);
          if (e) e.y = BY + (rr + 1) * CELL;
        }
      }
  }
  if (cleared) {
    total += cleared;
    level = 1 + Math.floor(total / 10);
    drop = Math.max(0.08, 0.5 - (level - 1) * 0.045);
    const word = cleared === 4 ? "TETRIS!" : cleared === 3 ? "triple" :
                 cleared === 2 ? "double" : "line";
    const msg = word + " · lv " + level;  // the banner carries the level
    say(msg);                             // the say law: 1.6 s of HUD
    showBanner(msg);                      // and the well's own echo
  }
}

function slide(dc) {
  if (fitsAt(0, dc)) {
    px += dc;
    paint();
  }
}

function turn() {
  if (SHAPES[cur].size === 2) return;    // the square has no moods
  const keep = rotN;
  for (const kick of [0, -1, 1, -2, 2]) {
    rotN = (keep + 1) % 4;
    const cand = shapeCells();
    const oldPx = px;
    px += kick;
    if (fits(cand)) { cells = cand; paint(); return; }
    px = oldPx;
  }
  rotN = keep;
}

function slam() {
  while (fitsAt(1, 0)) py += 1;
  paint();
  lock();
  sweep();
}

function reset() {
  for (const [, nm] of well) destroy(nm);
  well.clear();
  glows.clear();
  bannerT = 0;                           // a fresh well speaks nothing
  paintBanner();
  total = 0;
  level = 1;
  drop = 0.5;
  over = false;
  bag = [];
  nxt = null;
  held = null;
  holdUsed = false;
  spawn();
}

on.key((k) => {
  if (over) {
    if (k === "r") reset();
    return;
  }
  if (k === "left") slide(-1);
  else if (k === "right") slide(1);
  else if (k === "up" || k === "jump") turn();
  else if (k === "c") holdSwap();
  else if (k === "down" || k === "s") {
    if (fitsAt(1, 0)) py += 1;
    paint();                             // always repaint: the ghost must
  }                                      // hide the moment the order lands
  else if (k === "space") slam();
});

on.tick((d) => {
  // THE LIGHT LAWS RUN EVEN WHEN THE WORLD WAITS: the banner and the
  // locked cells' bloom wear at their honest rates on every tick,
  // game-over or not — the studio keeps the last light a wire game
  // sent, so a decay that stops at `over` is a flash-forever. Decay
  // runs FIRST (the birth-tick law): a light born later this very
  // tick shows whole.
  if (bannerT > 0) {
    bannerT = Math.max(0, bannerT - d);
    banner.glow = Math.max(0, banner.glow - 3 * d);
    paintBanner();
  }
  for (const [nm, g] of glows) {
    const ng = Math.max(0, g - 3 * d);
    if (ng === 0) glows.delete(nm); else glows.set(nm, ng);
    const e = find(nm);
    if (e) e.glow = ng;
  }
  if (over) return;
  dropT += d;
  if (dropT >= drop) {
    dropT = 0;
    if (fitsAt(1, 0)) {
      py += 1;
      paint();
    } else {
      lock();
      sweep();
    }
  }
  hud.text = `TETRIS  ·  arrows move · up turns · s sinks · space slams · c holds · ghost marks home · ${total} · lv ${level}`;
});

label("nxl", PX, PY + 9, "next", "#94a3b8");
label("hol", HX, HY + 9, "hold", "#94a3b8");
for (let i = 0; i < 4; ++i) piece.push(rect(`fall${i}`, -999, -999, CELL, CELL, "#8b5cf6"));
for (let i = 0; i < 4; ++i) ghost.push(rect(`ghost${i}`, -999, -999, CELL, CELL, "#8b5cf6"));
for (let i = 0; i < 4; ++i) pvue.push(rect(`pv${i}`, -999, -999, CELL, CELL, "#8b5cf6"));
for (let i = 0; i < 4; ++i) hv.push(rect(`hv${i}`, -999, -999, CELL, CELL, "#8b5cf6"));
spawn();

run();
