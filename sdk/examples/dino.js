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
// bites at 144 — and every touchdown leaves a fading dust. the leap
// lifts at 36 against the rise — an apex of 7.2 — because the desert
// grows shapes that demand it: the old apex of 5 could clear NOTHING
// (climb 5 at best, frame-perfect; the tall sentinel climb 7 — a wall,
// not a cactus). the skin probe survives a full run to prove it.
// the CACTI wear three shapes from ONE draw of the seed (short 3x3,
// the fat twin 6x4, the tall sentinel 3x5 — the stream is untouched,
// so the same run grows the same desert) and the sky's clock dresses
// them: green by day, pale by night with a faint halo of their own.
// the OWL hunts only at night, from its OWN seeded stream ("the night
// owl" — the desert's seed stays dedicated): it sweeps a band the
// grounded runner passes under, but any LEAP rises into it — the owl
// is the hazard that hunts the jump, not the runner. it launches only
// while the runner's feet are down and NOTHING is ahead of the runner
// (fair by construction), swoops at 1.8x the run, wings its own flap,
// and wears a halo of its own. and while an owl flies the desert
// HOLDS ITS BREATH — no cactus spawns — so the no-jump window is
// guaranteed clear: the owl never steals a leap a cactus demanded.
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
const CACTUS_DAY = "#34d399", CACTUS_NIGHT = "#a5f3fc";
const cacti = [];
for (let i = 0; i < CACTI; ++i) {
  const c = rect(`cactus-${i}`, -999, H - 8, 3, 5, "#34d399");
  c.tag = "hazard";
  cacti.push(c);
}

// the OWLS: two hunters parked off right, in a band the grounded
// runner passes under (rows H-13/H-12 — the standing head tops at
// H-9) but a leap climbs straight through. tag "hazard" — the same
// honest law: touch it and the run ends.
const OWLS = 2;
const OWL_COLOR = "#d8b4fe";
const owls = [];
for (let i = 0; i < OWLS; ++i) {
  const o = rect(`owl-${i}`, -999, H - 13, 5, 2, OWL_COLOR);
  o.tag = "hazard";
  o.glow = 2;                            // born wearing its own lantern
  owls.push(o);
}

// the owl's OWN seeded stream — the desert's seed stays dedicated
// (the sky already proved the law; the owl follows it)
let oseed = 0;
function initOwlSeed() {
  oseed = 2166136261 >>> 0;
  for (const ch of "the night owl") {
    oseed ^= ch.charCodeAt(0);
    oseed = (oseed * 16777619) >>> 0;
  }
}
initOwlSeed();
const onext = () => {
  oseed ^= oseed << 13; oseed >>>= 0;
  oseed ^= oseed >>> 17;
  oseed ^= oseed << 5;  oseed >>>= 0;
  return oseed / 4294967296;
};

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
let owlIn = 0;                           // seconds until the owl may ask
let owlFree = 0;                         // round-robin over the owl pool
let flapT = 0, flapUp = false;           // the wingbeat's own clock


function leap() {
  if (dead) return;
  if (dino.y >= H - 9) {                 // only from the ground
    vy = -36;                            // an apex of 7.2 — the desert's
    say("up!");                          // shapes are all honestly clearable
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
  owls.forEach((o) => { o.x = -999; });  // the hunters go home
  owlIn = 0;                             // and the owl clock restarts
  initOwlSeed();                         // the same run, the same owl
  owlFree = 0;
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
  const owlFlying = owls.some((o) => o.x > -100);  // read before anything moves
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
      vy = -36;
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
  // the spawn law: the seed decides, the pool serves — ONE draw for
  // the shape (short, the fat twin, tall — three bands, same stream),
  // ONE for the rest; the sky's clock dresses the skin for free.
  // WHILE AN OWL FLIES the desert holds its breath: no cactus spawns,
  // so nothing can demand a leap inside the owl's no-jump window.
  spawnIn -= dt;
  if (spawnIn <= 0 && !owlFlying) {
    const c = cacti[free % CACTI];
    free += 1;
    c.x = W + 2;
    const band = next();                 // one draw, as always
    if (band > 0.75) { c.h = 5; c.w = 3; }          // the tall sentinel
    else if (band > 0.4) { c.h = 4; c.w = 6; }      // the fat twin
    else { c.h = 3; c.w = 3; }                      // the short spire
    c.y = H - 3 - c.h;
    c.color = night ? CACTUS_NIGHT : CACTUS_DAY;    // the dress
    c.glow = night ? 1 : 0;                         // pale skins faintly ring
    spawnIn = 1.4 + next() * (90 / speed) + 0.5;
  }
  cacti.forEach((c) => {
    if (c.x > -100) c.x -= speed * dt;
    else if (c.x > -999 && c.x < -100) c.x = -999;   // walked off: park
  });
  // the owl's night shift: it asks every owlIn seconds, but launches
  // ONLY with the runner's feet down and NOTHING ahead of the runner
  // (parked or passed counts as clear). the draw happens only on a
  // real launch (waiting consumes no randomness).
  if (night) {
    owlIn -= dt;
    if (owlIn <= 0) {
      const feetDown = dino.y >= H - 9;
      const clearAhead = cacti.every((c) => c.x <= -999 || c.x + c.w <= dino.x);
      if (feetDown && clearAhead) {
        const o = owls[owlFree % OWLS];
        owlFree += 1;
        o.x = W + 2;
        o.y = H - 13;
        say("hoot hoot");
        owlIn = 6 + onext() * 8;         // one draw, on the owl's stream
      }
    }
  }
  owls.forEach((o) => {
    if (o.x > -100) {
      o.x -= speed * 1.8 * dt;           // the swoop: faster than the run
      flapT += dt;
      if (flapT >= 0.22) {               // the wingbeat, its own clock
        flapT = 0;
        flapUp = !flapUp;
      }
      o.y = H - 13 - (flapUp ? 1 : 0);   // the beat lifts, never dips
    } else if (o.x > -999 && o.x < -100) {
      o.x = -999;                        // flown off: park
    }
  });
  if (!night && meters >= 200) {         // the desert goes dark
    night = true;
    ground.color = "#2b2620";
    owlIn = 6;                           // the first owl no sooner than 6 s
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
