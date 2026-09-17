// THE LONG RUN in the DXN1 STUDIO — an endless runner on the wire.
// run:  dxn3 sdk/examples/dino.js
// space/jump leaps · the desert scrolls faster forever · the cacti
// come from a SEEDED shuffle — the same run, the same desert, forever.
// r walks again after the fall.
const dxn3 = require("dxn3");
const { rect, label, find, background, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#0f1117");

const hud = label("hud", 2, 1, "THE LONG RUN  ·  space to leap  ·  0 m");
const ground = rect("ground", 0, H - 3, W, 3, "#5b4a3a");
const dino = rect("dino", 6, H - 9, 7, 6, "#8b5cf6");
dino.tag = "player";

const clouds = [rect("cloud-a", 20, 6, 14, 2, "#2b3148"),
                rect("cloud-b", 70, 10, 18, 2, "#242a40")];

const CACTI = 6;                         // the pool: parked off right
const cacti = [];
for (let i = 0; i < CACTI; ++i) {
  const c = rect(`cactus-${i}`, -999, H - 8, 3, 5, "#34d399");
  c.tag = "hazard";
  cacti.push(c);
}

// the seed: the studio's law — deterministic stars, deterministic
// desert. FNV-1a of the runner's name, xorshift after.
let seed = 2166136261 >>> 0;
for (const ch of "the long run") {
  seed ^= ch.charCodeAt(0);
  seed = (seed * 16777619) >>> 0;
}
const next = () => {
  seed ^= seed << 13; seed >>>= 0;
  seed ^= seed >>> 17;
  seed ^= seed << 5;  seed >>>= 0;
  return seed / 4294967296;
};

let speed = 55, dist = 0, vy = 0, dead = false, night = false;
let spawnIn = 2.2;                       // seconds until the next cactus
let free = 0;                            // round-robin over the pool


function leap() {
  if (dead) return;
  if (dino.y >= H - 9) {                 // only from the ground
    vy = -30;
    say("up!");
  }
}

function walkAgain() {
  dead = false;
  dist = 0;
  speed = 55;
  vy = 0;
  dino.y = H - 9;
  cacti.forEach((c) => { c.x = -999; });
  spawnIn = 2.2;
  hud.text = "THE LONG RUN  ·  space to leap  ·  0 m";
}

on.key((k) => {
  if (k === "space" || k === "jump") leap();
  if (k === "r" && dead) walkAgain();
});

on.tick((dt) => {
  if (dead) return;
  // the run: the desert speeds up forever, the meters pile up
  speed += 2 * dt;
  dist += speed * dt;
  const meters = Math.floor(dist / 10);
  // physics: one honest gravity, the ground ends the fall
  vy += 90 * dt;
  dino.y = Math.min(H - 9, dino.y + vy * dt);
  if (dino.y >= H - 9) vy = 0;
  // the clouds parallax at a fifth of the run
  clouds.forEach((c, i) => {
    c.x -= (speed / 5) * dt * (i ? 1.3 : 1);
    if (c.x < -20) c.x = W + 4;
  });
  // the spawn law: the seed decides, the pool serves
  spawnIn -= dt;
  if (spawnIn <= 0) {
    const c = cacti[free % CACTI];
    free += 1;
    c.x = W + 2;
    const tall = next() > 0.6;
    c.h = tall ? 7 : 5;
    c.y = H - 3 - c.h;
    spawnIn = 1.4 + next() * (90 / speed) + 0.5;
  }
  cacti.forEach((c) => {
    if (c.x > -100) c.x -= speed * dt;
    else if (c.x > -999 && c.x < -100) c.x = -999;   // walked off: park
  });
  if (!night && meters >= 200) {         // the desert goes dark
    night = true;
    ground.color = "#2b2620";
    say("night falls at 200");
  }
  hud.text = `THE LONG RUN  ·  space to leap  ·  ${meters} m`;
});

on.hit((a, b) => {
  if (dead) return;
  const hazard = a.tag === "hazard" ? a : b;
  if (a.tag !== "player" && b.tag !== "player") return;
  dead = true;
  hazard.x = -999;
  const meters = Math.floor(dist / 10);
  win(`down at ${meters} m — r walks again`);
});

on.start(() => {
  dino.y = H - 9;
  cacti.forEach((c) => { c.x = -999; });
});

run();
