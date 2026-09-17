// pong.cpp — the C++ SDK's proof: a compiled game, hosted by the studio.
// you steer the left paddle (w/s chars), the engine feeds keys, the AI
// wants to win but caps its speed — and since the ladder, the cap
// BREATHES with the set: even score → L3 (the classic 190); you lead →
// the CPU digs in, up to L5 (285); the CPU leads → it eases off, down
// to L1 (120). A rubber band, honest on the hud ("CPU L3"), so a set
// stays dramatic on purpose — and the rung is VISIBLE: the AI paddle's
// halo IS its level (glow 1..5, the C++ SDK's own light since v3.1.46).
// run it:  dxn3 sdk/examples/pong.cpp
#include "../dxn3.hpp"

int main() {
    dxn3::Game g;
    g.background("#0d1522");

    auto* pad  = g.rect("pad",  24, dxn3::H / 2 - 30, 10, 60, "#38bdf8");
    pad->tag = "pad";
    auto* ai   = g.rect("ai",   dxn3::W - 34, dxn3::H / 2 - 30, 10, 60, "#fb7185");
    ai->tag = "ai";
    auto* ball = g.circle("ball", dxn3::W / 2 - 6, dxn3::H / 2 - 6, 12, 12, "#f8fafc");
    ball->tag = "ball";
    ball->vx = 240; ball->vy = 120;

    auto* hud  = g.label("hud",  16, 12, "YOU 0 · CPU 0 · first to 5 · CPU L3");
    auto* msg  = g.label("msg",  dxn3::W / 2 - 52, 40, "w/s to move — serve is live", "#fde047");
    int you = 0, cpu = 0;

    // the ladder: the CPU's speed cap per score state. Index 0 = L1.
    // L3 is the old constant 190 — an even set plays exactly as it
    // always did; the band only breathes when someone leads.
    const float LADDER[5] = {120.f, 155.f, 190.f, 235.f, 285.f};
    int lvl = 3;

    auto serve = [&](dxn3::Ent* b) {
        b->x = dxn3::W / 2 - 6;
        b->y = dxn3::H / 2 - 6;
        b->vx = 240 * ((you + cpu) % 2 ? -1.f : 1.f);
        b->vy = 120 * (((you + cpu) / 2) % 2 ? -1.f : 1.f);
    };

    g.onKey = [&](const std::string& k) {
        if (k == "w" || k == "s") {
            pad->y += (k == "s" ? 1.f : -1.f) * 420 * dxn3::dt;
            if (pad->y < 20) pad->y = 20;
            if (pad->y > dxn3::H - 80) pad->y = dxn3::H - 80;
        }
    };

    g.onTick = [&](float) {
        // the AI paddles with a capped speed — and the cap is the
        // ladder's rung: behind on the score, it digs in; ahead, it
        // eases off. The hud always names the rung it stands on.
        lvl = std::clamp(3 + you - cpu, 1, 5);
        float want = ball->y - ai->h / 2 + 6;
        float step = LADDER[lvl - 1] * dxn3::dt;
        if (ai->y < want) ai->y += std::min(step, want - ai->y);
        else              ai->y -= std::min(step, ai->y - want);

        // three walls bounce; passing a paddle scores
        if (ball->y < 22 || ball->y > dxn3::H - 34) ball->vy = -ball->vy;
        if (ball->x < 6)  { ++cpu; msg->text = "CPU scores!"; serve(ball); }
        if (ball->x > dxn3::W - 18) { ++you; msg->text = "you score!"; serve(ball); }
        if (you >= 5 || cpu >= 5) {
            msg->text = you > cpu ? "YOU WIN — ctrl+n for a new game"
                                  : "CPU wins — run it again";
            printf("%s wins the set\n", you > cpu ? "you" : "cpu");
            you = cpu = 0;
        }
        // the hud names the rung the NEW score stands on — a point
        // that lands this tick moves the rung with it. (The probe
        // caught the first speech mixing the pre-score rung with
        // post-score numbers; honesty means one score, one truth.)
        lvl = std::clamp(3 + you - cpu, 1, 5);
        ai->glow = lvl;         // v3.1.46: the rung is VISIBLE — L5's
                                // halo burns, L1's barely breathes
        hud->text = "YOU " + std::to_string(you) + " · CPU " +
                    std::to_string(cpu) + " · first to 5 · CPU L" +
                    std::to_string(lvl);
        g.var("score", you);
    };

    g.onHit = [&](dxn3::Ent& me, dxn3::Ent& other) {
        if (me.tag != "ball") return;
        // the paddle's edge steers the return, like the bricks example
        float off = (me.y + me.h / 2 - other.y) / other.h - 0.5f;
        me.vx = -me.vx * 1.03f;                 // speed up, honest drama
        me.vy = 320 * off;
        if (me.vx > 430) me.vx = 430;
        if (me.vx < -430) me.vx = -430;
    };

    g.run();
    return 0;
}
