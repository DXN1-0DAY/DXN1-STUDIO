// INVADERS in the DXN1 STUDIO — the classic march, on the engine's wire.
// run:  dxn3 sdk/examples/invaders.js
// left/right steer · space fires · the grid steps, drops and speeds up
// as it thins · parked bullets live off-screen until their gun needs
// them · four SHELTERS stand between the cannon and the order: every
// block drinks one shot (shot, bomb or the march itself) and is gone
// for good — honest destroys, not fading — r rebuilds from the ashes.
// the MYSTERY: every 13th shot from the gun (the old ROM's law) sums
// the saucer — it crosses the sky as its own lantern (glow 4), pays
// a bounty of 50/100/150/300, and the say speaks the SAME number the
// score keeps — their bombs cannot touch it; escaped or paid, it
// parks dark at the edge.
// the LIGHT: every wave GHOSTS IN (alpha 0.15 -> full over 0.9 s — the
// radar-field law; the sky literally fills again), the muzzle GLOWS
// (4) on fire and cools at eight a second, flying shots and bombs
// carry their own halo (2), and a spent bullet parks its light with
// its body.
// v3.1.78 — THE SECOND WAVE COMES IN THE DARK: the moon check's last
// fleet member goes night. Nine stars and a moon are born from their
// OWN seeded stream ("the night sky" — the march's unseeded dice never
// touch it), created first so the world renders over them, every star
// a rumor at alpha 0.15 and the moon a whisper at 0.25. The first
// cleared wave flips the sky — the say speaks it ("the sky fills
// again, darker now") and the fade law, honest in dt, runs over two
// seconds: nightT climbs dt/2, the stars ride 0.15 + 0.75 * nightT,
// the moon 0.25 + 0.75 * nightT — and at the fade's end the moon
// SHINES (glow 4) while the living march wears the cacti law's faint
// ring (glow 1, riding the same fade). A fresh run is a fresh day:
// restart (r) and EARTH HOLDS both pour the daylight back.
// v3.1.84 — THE DARK PAYS DOUBLE: the owl's twin visits the purse.
// The bounty is checked at PAYMENT time against the FULL night (the
// night flag AND nightT >= 1 — the owl's own threshold): under the
// full dark the purse's coin is paid twice — 100/200/300/600 — and
// the say says so ("the dark pays double"). By day, inside the fade,
// or after a fresh dawn, the honest purse stands. In the shooter the
// night is a hazard (the owl eats your shots); here the night is a
// harvest — clear the wave, and the sky pays you back.
const dxn3 = require("dxn3");
const { rect, circle, label, destroy, find, background, say, win, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#050814");

// the NIGHT'S FURNITURE — created FIRST so the world renders over it.
// Nine stars and a moon from their OWN seeded stream (the dino's
// law): the same run grows the same sky, forever, and the march's
// unseeded dice never shuffle it. Day: a rumor — the war starts in
// daylight; the dark is earned.
let nseed = 2166136261 >>> 0;
for (const ch of "the night sky") {
  nseed ^= ch.charCodeAt(0);
  nseed = (nseed * 16777619) >>> 0;
}
const nnext = () => {
  nseed ^= nseed << 13; nseed >>>= 0;
  nseed ^= nseed >>> 17;
  nseed ^= nseed << 5;  nseed >>>= 0;
  return nseed / 4294967296;
};
const stars = [];
for (let i = 0; i < 9; ++i) {
  const s = rect(`star-${i}`, 2 + Math.floor(nnext() * (W - 6)),
                 3 + Math.floor(nnext() * 9), 1, 1, "#e2e8f0");
  s.alpha = 0.15;
  stars.push(s);
}
const moon = circle("moon", W - 15, 4, 5, 5, "#f1f5f9");
moon.alpha = 0.25;
moon.glow = 0;                           // the moon waits for the dark
let night = false, nightT = 0;           // wave two earns the dark
function freshDay() {                    // a fresh run is a fresh day
  night = false;
  nightT = 0;
  stars.forEach((s) => { s.alpha = 0.15; });
  moon.alpha = 0.25;
  moon.glow = 0;
}

const hud = label("hud", 2, 1, "INVADERS  ·  left/right space  ·  score 0");
const player = rect("player", W >> 1, H - 4, 10, 4, "#8b5cf6");
player.tag = "player";

const ROWS_N = 3, COLS_N = 5;            // the marching order
const POINTS = [30, 20, 10];             // top rows pay best
const aliens = [];                       // 15 named seats, refilled per wave
for (let r = 0; r < ROWS_N; ++r)
  for (let c = 0; c < COLS_N; ++c) {
    const a = rect(`alien-${r}-${c}`, 0, 0, 7, 5, r === 0 ? "#f472b6" : "#fb7185");
    a.tag = "alien";
    a.row = r;
    aliens.push(a);
  }

// the guns' bullets are POOLS: parked at x -999 until fired — the wire
// only moves what changed, so a parked bullet costs nothing to keep
const shots = [];                        // the player's three
for (let i = 0; i < 3; ++i) {
  const s = rect(`shot-${i}`, -999, -999, 2, 4, "#facc15");
  s.tag = "pshot";
  shots.push(s);
}
const bombs = [];                        // the grid's three
for (let i = 0; i < 3; ++i) {
  const b = rect(`bomb-${i}`, -999, -999, 2, 4, "#34d399");
  b.tag = "abomb";
  bombs.push(b);
}

// the MYSTERY SAUCER: parked at x -999 like the bullets until the
// gun's 13th shot calls it — it rides ABOVE the grid (y 0..3 never
// touches row 0 at y 5) and is its own lantern while it flies
const saucer = rect("saucer", -999, 0, 12, 3, "#22d3ee");
saucer.tag = "ufo";
let shotCount = 0, saucerVx = 0;         // the gun's tally; 0 = parked

const UFOS = [50, 100, 150, 300];        // the mystery's purse
let wave = 1, score = 0, lives = 3, alive = 15;
let dir = 1, stepT = 0, stepEvery = 0.8, fireT = 1.5, gunCool = 0, over = false;
let waveT = 1;                           // the ghost-in clock (deploy resets it)
const SPEEDS = { 15: 0.8, 10: 0.55, 5: 0.35, 1: 0.2 };   // thinner = faster

// the SHELTERS: four arches of 7 blocks each — every block absorbs one
// hit (your shot, their bomb, or the march grinding through) and is
// destroyed for good. Erosion you can SEE: the arch thins until only
// the shoulders stand, and a fresh run pours new concrete.
let bunkers = [];
function buildShields() {
  bunkers = [];
  const SH_Y = 32, ARCH = [[0, 0], [1, 0], [2, 0], [0, 1], [0, 2], [2, 1], [2, 2]];
  for (let k = 0; k < 4; ++k) {
    const bx = 12 + k * 20;
    ARCH.forEach(([cx, cy], i) => {
      const e = rect(`shield-${k}-${i}`, bx + cx * 3, SH_Y + cy * 2, 3, 2, "#38bdf8");
      e.tag = "shield";
      bunkers.push(e);
    });
  }
}
buildShields();

function deploy() {
  alive = ROWS_N * COLS_N;
  stepEvery = SPEEDS[alive] || 0.2;
  dir = 1;
  waveT = 0;                             // the new order arrives as ghosts
  const left = 8 + Math.min(4, wave - 1) * 2;   // each wave starts lower
  aliens.forEach((a, i) => {
    const r = Math.floor(i / COLS_N), c = i % COLS_N;
    a.x = left + c * 9;
    a.y = 5 + r * 6 + Math.min(3, wave - 1);
    a.visible = 1;
  });
}

function grab(pool) {                    // a parked bullet, or none
  return pool.find((b) => b.x < -100) || null;
}

function summon() {                      // the mystery takes the sky
  const fromLeft = Math.random() < 0.5;
  saucer.x = fromLeft ? -12 : W + 2;
  saucerVx = fromLeft ? 16 : -16;        // one crossing, then it rests
  saucer.glow = 4;                       // it IS its own lantern
  say("something crosses the sky…");
}

function park() {                        // the mystery rests dark, wherever it was
  saucerVx = 0;
  saucer.x = -999;
  saucer.glow = 0;
}

function fire() {
  const s = grab(shots);
  if (!s || gunCool > 0) return;
  s.x = player.x + 4;
  s.y = player.y - 4;
  s.glow = 2;                            // the flying shot carries its halo
  player.glow = 4;                       // the muzzle speaks (keys fire after
  gunCool = 0.3;                         //   the tick, so the frame gets the 4)
  shotCount += 1;
  if (shotCount % 13 === 0 && saucerVx === 0) summon();   // every 13th shot
}

function alienFire() {
  const gunners = aliens.filter((a) => a.visible);
  if (!gunners.length) return;
  const b = grab(bombs);
  if (!b) return;
  const g = gunners[Math.floor(Math.random() * gunners.length)];
  b.x = g.x + 2;
  b.y = g.y + 5;
  b.glow = 2;                            // their bombs fly lit too
}

function rebuild(msg) {                  // the wave is spent — the next lands
  say(msg);
  wave += 1;
  if (wave === 2 && !night) night = true;   // the second wave comes in the dark
  if (wave > 3) {
    win("EARTH HOLDS");
    wave = 1;
    score = 0;
    lives = 3;
    buildShields();                      // a fresh run pours new concrete
    park();                              // the sky empties for the new run
    shotCount = 0;
    freshDay();                          // earth held — a fresh day dawns
  }
  deploy();
}

function restart() {                     // r from the ashes
  over = false;
  wave = 1;
  score = 0;
  lives = 3;
  alive = ROWS_N * COLS_N;
  buildShields();
  deploy();
  park();                                // the mystery forgets this run too
  freshDay();                            // a fresh run is a fresh day
  shotCount = 0;
  gunCool = 0;
  hud.text = "INVADERS  ·  score 0  ·  lives 3";
  say("the cannon is reborn");
}

on.key((k) => {                       // held keys fire per frame —
  if (over) {
    if (k === "r") restart();
    return;
  }
  if (k === "left") player.x = Math.max(1, player.x - 1);
  else if (k === "right") player.x = Math.min(W - 11, player.x + 1);
  else if (k === "space") fire();
});

on.tick((dt) => {
  if (over) return;
  gunCool = Math.max(0, gunCool - dt);
  // the ghost-in: every wave (and the shelters with it) fades from
  // alpha 0.15 to full over 0.9 s — the radar-field law
  waveT = Math.min(1, waveT + dt / 0.9);
  const A = 0.15 + 0.85 * waveT;
  aliens.forEach((a) => { if (a.visible) a.alpha = A; });
  bunkers.forEach((s) => { s.alpha = A; });
  if (night && nightT < 1) {             // the sky fades in over two seconds
    nightT = Math.min(1, nightT + dt / 2);
    stars.forEach((s) => { s.alpha = 0.15 + 0.75 * nightT; });
    moon.alpha = 0.25 + 0.75 * nightT;
    moon.glow = nightT >= 1 ? 4 : 0;     // and then the moon shines
    aliens.forEach((a) => { if (a.visible) a.glow = nightT; });  // the cacti
  }                                      //   law: the march rings faintly
  player.glow = Math.max(0, (player.glow || 0) - 8 * dt);   // the muzzle cools
  // the march: a discrete step, faster as the grid thins
  stepT += dt;
  if (stepT >= stepEvery) {
    stepT = 0;
    const living = aliens.filter((a) => a.visible);
    const xs = living.map((a) => a.x);
    const edge = dir > 0 ? Math.max(...xs, 0) : Math.min(...xs, W);
    if ((dir > 0 && edge > W - 12) || (dir < 0 && edge < 2)) {
      dir = -dir;
      living.forEach((a) => { a.y += 2; });          // the drop
    } else {
      living.forEach((a) => { a.x += 2 * dir; });
    }
    stepEvery = SPEEDS[living.length] || 0.2;
    if (living.some((a) => a.y > H - 9)) {           // the grid lands — invasion
      lives -= 1;
      hud.text = `INVADERS  ·  score ${score}  ·  lives ${lives}`;
      if (lives <= 0) { over = true; win("EARTH FALLS"); return; }
      deploy();
      return;
    }
  }
  fireT -= dt;
  if (fireT <= 0) { fireT = 0.7 + Math.random() * 1.6; alienFire(); }
  // the bullets fly; parked ones sleep off-screen, dark
  shots.forEach((s) => { if (s.x > -100) { s.y -= 40 * dt; if (s.y < 0) { s.x = -999; s.glow = 0; } } });
  bombs.forEach((b) => { if (b.x > -100) { b.y += 22 * dt; if (b.y > H) { b.x = -999; b.glow = 0; } } });
  // the mystery crosses; past the far edge it parks dark and the
  // gun's tally starts counting toward the next summons
  if (saucerVx !== 0) {
    saucer.x += saucerVx * dt;
    if (saucer.x < -14 || saucer.x > W + 14) park();
  }
});

on.hit((a, b) => {
  if (over) return;
  const pair = [a.tag, b.tag].sort().join("|");
  if (pair === "alien|pshot") {
    const alien = a.tag === "alien" ? a : b;
    const shot = a.tag === "alien" ? b : a;
    score += POINTS[alien.row] || 10;
    alien.visible = 0;                 // the seat stays, the body is gone
    alien.y = -50;
    shot.x = -999;
    shot.glow = 0;                     // the spent shot parks its light
    alive -= 1;
    hud.text = `INVADERS  ·  score ${score}  ·  lives ${lives}`;
    if (alive === 0)
      rebuild(wave === 1
        ? "wave 1 cleared — the sky fills again, darker now"
        : `wave ${wave} cleared — the sky fills again`);
  } else if (pair === "abomb|player") {
    const bomb = a.tag === "abomb" ? a : b;
    bomb.x = -999;
    bomb.glow = 0;
    lives -= 1;
    say("ouch — the cannon took one");
    hud.text = `INVADERS  ·  score ${score}  ·  lives ${lives}`;
    if (lives <= 0) { over = true; win("EARTH FALLS"); }
  } else if (pair === "pshot|shield") {
    const block = a.tag === "shield" ? a : b;
    const shot = a.tag === "shield" ? b : a;
    destroy(block.name);               // your own shot eats the shelter
    shot.x = -999;
    shot.glow = 0;
  } else if (pair === "abomb|shield") {
    const block = a.tag === "shield" ? a : b;
    const bomb = a.tag === "abomb" ? a : b;
    destroy(block.name);               // their bomb eats it too
    bomb.x = -999;
    bomb.glow = 0;
  } else if (pair === "alien|shield") {
    const block = a.tag === "shield" ? a : b;
    destroy(block.name);               // the march grinds what it touches
  } else if (pair === "pshot|ufo") {
    const ufo = a.tag === "ufo" ? a : b;
    const shot = a.tag === "ufo" ? b : a;
    const pay = UFOS[Math.floor(Math.random() * UFOS.length)];
    const dark = night && nightT >= 1;   // the owl's law: only the FULL dark
    const paid = dark ? pay * 2 : pay;   // the dark pays double — the night
    score += paid;                       //   is a harvest, not a hazard
    park();                              // the mystery rests dark, paid
    shot.x = -999;
    shot.glow = 0;
    say(dark
      ? `the mystery pays ${paid} — the dark pays double`
      : `the mystery pays ${paid}`);     // the say speaks the SAME number
    hud.text = `INVADERS  ·  score ${score}  ·  lives ${lives}`;
  } else if (pair === "alien|player") {
    lives = 0;
    over = true;
    win("EARTH FALLS");
  }
});

on.start(() => {
  deploy();
  hud.text = "INVADERS  ·  left/right space  ·  score 0";
});

run();
