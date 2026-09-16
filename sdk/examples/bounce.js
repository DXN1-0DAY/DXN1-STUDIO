:recent
:recent ghost.py
// bounce.js — pong-alone: a ball, walls, a paddle YOU steer, bricks to break.
// run it from the studio:   dxn3 sdk/examples/bounce.js
const dxn3 = require("dxn3");
const { rect, circle, label, destroy, background, on, run } = dxn3;
const W = dxn3.W, H = dxn3.H;

background("#04101c");

const pad = rect("pad", W / 2 - 40, H - 14, 80, 10, "#38bdf8");
pad.tag = "pad";
const ball = circle("ball", W / 2, H - 40, 12, 12, "#f8fafc");
ball.tag = "ball";
ball.vx = 260; ball.vy = -300;

const hud = label("hud", 16, 14, "BRICKS 12 · BALLS 3");
let bricks = 0, balls = 3;

// the wall of bricks
let n = 0;
for (let row = 0; row < 3; ++row)
  for (let col = 0; col < 6; ++col) {
    const b = rect("brick" + n, 60 + col * 130, 80 + row * 40, 110, 24,
                   ["#fb7185", "#facc15", "#34d399"][row]);
    b.tag = "brick";
    ++n;
  }

on.key((k) => {
  if (k === "left") pad.x = Math.max(4, pad.x - 480 * dxn3.dt);
  if (k === "right") pad.x = Math.min(W - 84, pad.x + 480 * dxn3.dt);
});

on.tick(() => {
  // the ball bounces off three walls; the floor costs a ball
  if (ball.x < 4 || ball.x > W - 16) ball.vx = -ball.vx;
  if (ball.y < 30) ball.vy = -ball.vy;
  if (ball.y > H - 8) {
    balls -= 1;
    ball.x = W / 2; ball.y = H - 40;
    ball.vy = -300; ball.vx = 260 * (Math.random() < 0.5 ? -1 : 1);
    if (balls <= 0) label("over", W / 2 - 60, H / 2 - 10,
                          "GAME OVER — ctrl+r to retry", "#fb7185");
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
    if (bricks >= 12) label("win", W / 2 - 70, H / 2 - 10,
                            "CLEARED! you built this with code.", "#34d399");
  } else if (other.tag === "pad") {
    // steer: hitting the paddle's edge angles the ball
    const off = (me.x - other.x) / other.w - 0.5;
    ball.vx = 420 * off;
    if (ball.vy > 0) ball.vy = -Math.abs(ball.vy);
  }
});

run();
