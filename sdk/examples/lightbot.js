// THE NIGHT SHIFT in the DXN1 STUDIO — a lightbot puzzle on the wire.
// run:  dxn3 sdk/examples/lightbot.js
// arrows/jump walk the grid · space lights the lamp under you ·
// every lamp wears glow (v3.1.20's law) — light the whole city, rest.
// r takes the shift again.
const dxn3 = require("dxn3");
const { rect, label, background, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#070912");                 // the beacon's sky — a city at 3am

const hud = label("hud", 2, 1,
  "THE NIGHT SHIFT  ·  arrows walk · space lights · 0/12 lit, 0 steps");
const tag = label("tag", 2, H - 2, "the city sleeps when the grid is gold");

// the grid: 7 columns, 5 rows, tiles 6x6, centred under the hud
const COLS = 7, ROWS = 5, T = 6;
const GX = Math.floor((W - COLS * T) / 2), GY = 9;

// the puzzle: a diamond of twelve lamps (1 = waits for light)
const LAMPS = [
  "0010100",
  "0101010",
  "1000001",
  "0101010",
  "0010100",
];

// 35 tiles, one entity each — dark slate until a lamp wakes up
const tiles = [];
for (let r = 0; r < ROWS; ++r)
  for (let c = 0; c < COLS; ++c) {
    const lamp = LAMPS[r][c] === "1";
    const t = rect(`r${r}c${c}`, GX + c * T, GY + r * T, T - 1, T - 1,
                   lamp ? "#3a3120" : "#141826");
    t.tag = "tile";
    t.lamp = lamp;
    t.lit = false;
    tiles.push(t);
  }

const bot = rect("bot", GX + 3 * T + 1, GY + 2 * T + 1, 4, 4, "#8b5cf6");
bot.tag = "player";
bot.glow = 2;                          // the head-lamp you start with

let col = 3, row = 2;                  // the bot starts dead centre
let lit = 0, steps = 0, won = false, pulse = 0;
const LAMP_TOTAL = tiles.filter(t => t.lamp).length;   // the honest count: 12
let moveCD = 0;                        // held keys fire every frame — throttle

const here = () => tiles[row * COLS + col];

function walk(dc, dr) {
  if (won) return;
  const nc = col + dc, nr = row + dr;
  if (nc < 0 || nc >= COLS || nr < 0 || nr >= ROWS) {
    say("the grid ends there");        // honest walls
    return;
  }
  col = nc; row = nr; steps += 1; moveCD = 0.11;
  bot.x = GX + col * T + 1;
  bot.y = GY + row * T + 1;
}

function light() {
  if (won) return;
  const t = here();
  if (!t.lamp) { say("no lamp on this tile"); return; }
  if (t.lit) { say("already burning"); return; }
  t.lit = true; lit += 1;
  t.color = "#facc15";
  t.glow = 3;                          // v3.1.20's law, used as the POINT
  if (lit === LAMP_TOTAL) {
    won = true;
    const grade = steps <= 42 ? "a ghost of the grid"
                : steps <= 60 ? "steady hands"
                : "the long way home";
    win(`the city sleeps easy — ${steps} steps, ${grade} — r for one more shift`);
  } else {
    say(`lit ${lit}/${LAMP_TOTAL}`);
  }
}

function shiftAgain() {
  won = false; lit = 0; steps = 0; col = 3; row = 2; moveCD = 0;
  bot.x = GX + col * T + 1; bot.y = GY + row * T + 1; bot.glow = 2;
  for (const t of tiles) {
    if (t.lamp) { t.lit = false; t.color = "#3a3120"; t.glow = 0; }
  }
  say("the shift begins again");
}

on.key((k) => {
  if (moveCD > 0) return;
  if (k === "left") walk(-1, 0);
  else if (k === "right") walk(1, 0);
  else if (k === "jump" || k === "w") walk(0, -1);
  else if (k === "s") walk(0, 1);
  else if (k === "space") light();
  else if (k === "r") shiftAgain();
});

on.tick((dt) => {
  if (moveCD > 0) moveCD -= dt;
  if (won) {                           // the done shift breathes
    pulse += dt;
    bot.glow = Math.sin(pulse * 5) > 0 ? 5 : 3;
  }
  hud.text = won
    ? `THE NIGHT SHIFT  ·  the city is gold · ${lit}/${LAMP_TOTAL} lit, ${steps} steps`
    : `THE NIGHT SHIFT  ·  arrows walk · space lights · ${lit}/${LAMP_TOTAL} lit, ${steps} steps`;
});

run();
