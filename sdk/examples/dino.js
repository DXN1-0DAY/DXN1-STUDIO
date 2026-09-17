// THE LONG RUN in the DXN1 STUDIO — an endless runner on the wire.
// run:  dxn3 sdk/examples/dino.js
// space/jump leaps · the desert scrolls faster forever · the cacti
// come from a SEEDED shuffle — the same run, the same desert, forever.
// the NIGHT SKY (stars + moon) comes from its OWN seed — the desert's
// seed stays dedicated — and the alpha law fades it in at 200 m:
// day alpha 0.15, night alpha 0.9, and then the moon shines.
// the GRACE LAW: a press that arrives while airborne is kept for
// 0.12 s — if the ground lands before the press expires, the leap
// fires anyway ("kept" at the press, "grace!" on the second chance).
// the arc is asymmetric on purpose: the rise floats at 90, the fall
// bites at 144 — and every touchdown leaves a fading dust.
// r walks again after the fall.
const dxn3 = require("dxn3");
const { rect, circle, label, find, background, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#0f1117");

const hud = label("hud", 2, 1, "THE LONG RUN  ·  space to leap  ·  0 m");
const ground = rect("ground", 0, H - 3, W, 3, "#5b4a3a");
const dino = rect("dino", 6, H - 9, 7, 6, "#8b5cf6");
dino.tag = "player";
const dust = rect("dust", -999, H - 4, 3, 1, "#9ca3af");  // parked; the feet speak
dust.alpha = 0;

const clouds = [rect("cloud-a", 20, 6, 14, 2, "#2b3148"),
                rect("cloud-b", 70, 10, 18, 2, "#242a40")];

// the NIGHT SKY: seven stars and a moon from their own seeded stream
// (the cactus seed is the desert's alone — the sky never shuffles it).
// Day: alpha 0.15, a rumor. The run passes 200 m and the alpha law
// fades the sky in over two seconds — the engine's field as weather.
let sseed = 2166136261 >>> 0;
for (const ch of "the night sky") {
  sseed ^= ch.charCodeAt(0);
  sseed = (sseed * 16777619) >>> 0;
}
const snext = () => {
  sseed ^= sseed << 13; sseed >>>= 0;
  sseed ^= sseed >>> 17;
  sseed ^= sseed << 5;  sseed >>>= 0;
  return sseed / 4294967296;
};
const sky = [];
for (let i = 0; i < 7; ++i) {
  const s = rect(`star-${i}`, 2 + Math.floor(snext() * (W - 6)),
                 3 + Math.floor(snext() * 9), 1, 1, "#e2e8f0");
  s.alpha = 0.15;
  sky.push(s);
}
const moon = circle("moon", W - 15, 4, 5, 5, "#f1f5f9");
moon.alpha = 0.25;

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

let speed = 55, dist = 0, vy = 0, dead = false, night = false, nightT = 0;
let spawnIn = 2.2;                       // seconds until the next cactus
let free = 0;                            // round-robin over the pool
let bufT = 0;                            // the grace memory: a kept press


function leap() {
  if (dead) return;
  if (dino.y >= H - 9) {                 // only from the ground
    vy = -30;
    say("up!");
  } else {
    bufT = 0.12;                         // the early press is kept
    say("kept");
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
  bufT = 0;                              // a fresh run keeps nothing
  dust.x = -999;
  dust.alpha = 0;
  night = false;                         // a fresh run is a fresh day
  nightT = 0;
  ground.color = "#5b4a3a";
  sky.forEach((s) => { s.alpha = 0.15; });
  moon.alpha = 0.25;
  moon.glow = 0;
  clouds.forEach((c) => { c.alpha = 1; });
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
  // the dust fades in its own light — never in the tick it is born
  if (dust.alpha > 0) {
    dust.alpha = Math.max(0, dust.alpha - 2.8 * dt);
    if (dust.alpha === 0) dust.x = -999;
  }
  // physics: one honest gravity with a bite — the rise floats at 90,
  // the fall drops at 144, the ground ends the fall, and a press
  // that arrived early still lands (the grace law)
  const wasAir = dino.y < H - 9;
  vy += (vy < 0 ? 90 : 144) * dt;
  dino.y = Math.min(H - 9, dino.y + vy * dt);
  if (wasAir && dino.y >= H - 9) {       // the touchdown: the feet speak
    dust.x = dino.x + 2;
    dust.y = H - 4;
    dust.alpha = 0.7;
    if (bufT > 0) {                      // the second chance fires
      bufT = 0;
      vy = -30;
      say("grace!");
    } else {
      vy = 0;
    }
  } else if (dino.y >= H - 9) {
    vy = 0;
  }
  bufT = Math.max(0, bufT - dt);         // the memory decays honestly
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
  if (night && nightT < 1) {             // the sky fades in over two seconds
    nightT = Math.min(1, nightT + dt / 2);
    sky.forEach((s) => { s.alpha = 0.15 + 0.75 * nightT; });
    moon.alpha = 0.25 + 0.75 * nightT;
    moon.glow = nightT >= 1 ? 4 : 0;     // and then the moon shines
    clouds.forEach((c) => { c.alpha = 1 - 0.5 * nightT; });
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
