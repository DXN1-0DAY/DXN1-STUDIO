// TETRIS in the DXN1 STUDIO — the falling order, on the engine's wire.
// run:  dxn3 sdk/examples/tetris.js
// left/right move · up (or jump) rotates · s soft-drops · space
// slams · the GHOST wears alpha 0.32 where the order will land (the
// engine's alpha law as honest wayfinding) · the locked cells LIVE
// as entities (one rect per seat, named by its place) and a cleared
// line is ten honest destroys · the bag is SEEDED: the same run, the
// same falls, forever.  (soft-drop rides the LETTER s: the wire's
// held keys are left/right/jump/space — "down" never rides it; the
// ghost probe exposed that latent bug.)
const dxn3 = require("dxn3");
const { rect, label, destroy, find, background, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#0a0c16");

const hud = label("hud", 2, 1, "TETRIS  ·  arrows move · up turns · s sinks · space slams · ghost marks home · 0");

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
let cur = "T", rotN = 0, px = 4, py = -1, cells = [];
let bag = [], dropT = 0, drop = 0.5, total = 0, level = 1, over = false, seq = 0;

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

function spawn() {
  cur = pull();
  rotN = 0;
  px = COLS >> 1;
  py = -1;
  cells = shapeCells();
  piece.forEach((e) => { e.color = SHAPES[cur].color; });
  if (!fits(cells)) {
    over = true;
    piece.forEach((e) => { e.visible = 0; });
    ghost.forEach((e) => { e.visible = 0; });
    win(`TOPPED OUT at ${total} — r falls again`);
    return;
  }
  paint();
}

function lock() {
  // every locked cell becomes ITS OWN entity (named by sequence) — the
  // falling seats must stay free for the next order, or a sweep would
  // destroy the piece that is falling
  cells.forEach(([r, c], i) => {
    if (py + r < 0) return;
    const nm = `cell${seq}`;
    seq += 1;
    rect(nm, BX + (px + c) * CELL, BY + (py + r) * CELL, CELL, CELL,
         SHAPES[cur].color);
    well.set(key(py + r, px + c), nm);
  });
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
      destroy(well.get(key(r, c)));
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
    say(cleared === 4 ? "TETRIS!" : cleared === 3 ? "triple" :
        cleared === 2 ? "double" : "line");
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
  total = 0;
  level = 1;
  drop = 0.5;
  over = false;
  bag = [];
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
  else if (k === "down" || k === "s") {
    if (fitsAt(1, 0)) py += 1;
    paint();                             // always repaint: the ghost must
  }                                      // hide the moment the order lands
  else if (k === "space") slam();
});

on.tick((d) => {
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
  hud.text = `TETRIS  ·  arrows move · up turns · s sinks · space slams · ghost marks home · ${total} · lv ${level}`;
});

for (let i = 0; i < 4; ++i) piece.push(rect(`fall${i}`, -999, -999, CELL, CELL, "#8b5cf6"));
for (let i = 0; i < 4; ++i) ghost.push(rect(`ghost${i}`, -999, -999, CELL, CELL, "#8b5cf6"));
spawn();

run();
