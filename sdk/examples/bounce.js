// bounce.js — pong-alone: a ball, walls, a paddle YOU steer, bricks to break.
// run it from the studio:   dxn3 sdk/examples/bounce.js
// THE WALL FITS THE ROOM: the host sends the console's own pixels
// (one column wide, two rows tall), so the brick wall is sized from
// W and H — twelve bricks, four across, three deep, every one on
// screen, the win actually reachable. The ball is the room's
// lantern and leaves a COMET behind it — six seats that slide back
// one each tick, wearing their ages as alpha (0.5 down to 0.10);
// the pad answers a touch with a glow that decays at twelve a
// second; a lost ball parks the comet and the next serve re-forms it.
// v3.1.69 — the wear audit came for the room: a brick BITE makes the
// lantern FLARE (glow 4, worn back to its resting 2 by the honest
// 3/s — a flare with a floor, never a flash-forever and never a
// light below its rest), and the end plaques (the win, the game
// over) are born with a bloom of glow 3 that wears at the house's
// 3/s — the words stay, the light tells the truth about its age.
const dxn3 = require("dxn3");
const { rect, circle, label, destroy, background, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#04101c");

const pad = rect("pad", W / 2 - 40, H - 14, 80, 10, "#38bdf8");
pad.tag = "pad";
const ball = circle("ball", W / 2, H - 40, 12, 12, "#f8fafc");
ball.tag = "ball";
ball.vx = 260; ball.vy = -300;
ball.glow = 2;                           // the room's lantern

// the comet: six seats behind the ball, youngest to oldest
const TRAIL_A = [0.5, 0.42, 0.34, 0.26, 0.18, 0.10];
const trail = [];
for (let i = 0; i < TRAIL_A.length; ++i) {
  const t = rect("trail-" + i, -999, -999, 6, 6, "#7dd3fc");
  t.alpha = 0;
  trail.push(t);
}
let px = ball.x, py = ball.y;            // the seat the ball just left

let plaque = null, plaqueGlow = 0;       // the end plaques' honest bloom

const hud = label("hud", 2, 1, "BRICKS 12 LEFT · BALLS 3");
let bricks = 0, balls = 3;

function speak(kind) {                   // the room's end plaques: born
  const text = kind === "win" ?          // whole (glow 3), worn 3/s
    "CLEARED! you built this with code." : "GAME OVER — ctrl+r to retry";
  const color = kind === "win" ? "#34d399" : "#fb7185";
  plaque = label(kind, W / 2 - 70, H / 2 - 10, text, color);
  plaque.glow = 3;
  plaqueGlow = 3;
}

// the wall of bricks — four across, three deep, sized to the room
const COLS = 4, ROWS = 3;
const BW = Math.max(12, Math.floor((W - 24) / COLS) - 4), BH = 8;
let n = 0;
for (let row = 0; row < ROWS; ++row)
  for (let col = 0; col < COLS; ++col) {
    const b = rect("brick" + n, 8 + col * (BW + 4), 10 + row * (BH + 4),
                   BW, BH, ["#fb7185", "#facc15", "#34d399"][row]);
    b.tag = "brick";
    ++n;
  }

on.key((k) => {
  if (k === "left") pad.x = Math.max(4, pad.x - 480 * dxn3.dt);
  if (k === "right") pad.x = Math.min(W - 84, pad.x + 480 * dxn3.dt);
});

on.tick(() => {
  // the plaques' light wears at the house's 3/s — decay runs FIRST
  // (the birth-tick law): a plaque lit later this very tick shows whole
  if (plaqueGlow > 0) {
    plaqueGlow = Math.max(0, Math.round((plaqueGlow - 3 * dxn3.dt) * 1000) / 1000);
    if (plaque) plaque.glow = plaqueGlow;
  }
  // the lantern's flare wears back to its resting 2 — a flare with a
  // floor: it never dips below the lantern's own honest rest
  ball.glow = Math.max(2, ball.glow - 3 * dxn3.dt);
  // the comet: each seat slides back one, the young seat takes the
  // spot the ball just left; every seat wears its own age as alpha
  for (let i = trail.length - 1; i > 0; --i) {
    trail[i].x = trail[i - 1].x;
    trail[i].y = trail[i - 1].y;
  }
  trail[0].x = px; trail[0].y = py;
  trail.forEach((t, i) => { t.alpha = TRAIL_A[i]; });
  px = ball.x; py = ball.y;
  // the pad's answer fades at twelve a second — and never in the
  // tick it was lit (hits fire after the tick, so the touch frame
  // carries the full 3)
  pad.glow = Math.max(0, (pad.glow || 0) - 12 * dxn3.dt);
  // the ball bounces off the top wall; the floor costs a ball
  if (ball.x < 4 || ball.x > W - 16) ball.vx = -ball.vx;
  if (ball.y < 2) ball.vy = -ball.vy;
  if (ball.y > H - 8) {
    balls -= 1;
    ball.x = W / 2; ball.y = H - 40;
    ball.vy = -300; ball.vx = 260 * (Math.random() < 0.5 ? -1 : 1);
    px = ball.x; py = ball.y;
    trail.forEach((t) => { t.x = -999; t.y = -999; t.alpha = 0; });
    if (balls <= 0 && !plaque) speak("over");
  }
  hud.text = "BRICKS " + (12 - bricks) + " LEFT · BALLS " + balls;
});

on.hit((a, b) => {
  const me = a.tag === "ball" ? a : b;
  const other = a.tag === "ball" ? b : a;
  if (other.tag === "brick") {
    destroy(other.name);
    bricks += 1;
    ball.vy = -ball.vy;
    ball.glow = 4;                     // the bite: the lantern FLARES
                                       // (worn back to its resting 2
                                       // by the tick's 3/s staircase)
    if (bricks >= 12 && !plaque) speak("win");
  } else if (other.tag === "pad") {
    // steer: hitting the paddle's edge angles the ball
    const off = (me.x - other.x) / other.w - 0.5;
    ball.vx = 420 * off;
    if (ball.vy > 0) ball.vy = -Math.abs(ball.vy);
    pad.glow = 3;                        // the pad answers the touch
  }
});

run();
