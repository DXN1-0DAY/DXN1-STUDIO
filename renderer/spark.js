// ============================================================
// SPARK — the 2D engine built into DXN1 STUDIO 3.
// Entities · AABB physics · platformer controller · camera ·
// particles · input · delta-time loop. Scenes are plain JSON
// (scenes/*.dxn1.json) so the editor, the engine and the disk
// all speak the same shape.
// ============================================================
"use strict";

const Spark = (() => {

  // ------------------------------------------------------------ schema
  // entity: {name, x, y, w, h, shape:"rect"|"circle", color,
  //          vx, vy, solid, gravity:boolean(default: scene gravity),
  //          controls:"platformer"|"none", tag, bounce:0..1, alive:true}
  // scene:  {name, bg, gravity, camera:{x,y,zoom}, entities:[...]}

  function makeEntity(patch) {
    return Object.assign({
      name: "entity", x: 0, y: 0, w: 36, h: 36,
      shape: "rect", color: "#8b5cf6",
      vx: 0, vy: 0, solid: false, gravity: null,
      controls: "none", tag: "", bounce: 0, alive: true,
    }, patch || {});
  }

  function demoScene() {
    return {
      name: "playground",
      bg: "#0b0e1a",
      gravity: 1500,
      camera: { x: 0, y: 0, zoom: 1 },
      entities: [
        { name: "player", x: 90, y: 300, w: 34, h: 44, color: "#8b5cf6",
          controls: "platformer", solid: true, tag: "player" },
        { name: "ground", x: -200, y: 430, w: 1400, h: 90, color: "#1c2136", solid: true },
        { name: "ledge-a", x: 300, y: 330, w: 170, h: 22, color: "#1c2136", solid: true },
        { name: "ledge-b", x: 560, y: 250, w: 150, h: 22, color: "#1c2136", solid: true },
        { name: "ledge-c", x: 800, y: 170, w: 150, h: 22, color: "#1c2136", solid: true },
        { name: "coin-1", x: 345, y: 280, w: 22, h: 22, shape: "circle", color: "#fbbf24", tag: "coin" },
        { name: "coin-2", x: 405, y: 280, w: 22, h: 22, shape: "circle", color: "#fbbf24", tag: "coin" },
        { name: "coin-3", x: 615, y: 200, w: 22, h: 22, shape: "circle", color: "#fbbf24", tag: "coin" },
        { name: "coin-4", x: 855, y: 120, w: 22, h: 22, shape: "circle", color: "#fbbf24", tag: "coin" },
        { name: "bouncer", x: 1030, y: 380, w: 90, h: 22, color: "#22d3ee", solid: true, bounce: 1.4, tag: "bouncy" },
        { name: "ball", x: 640, y: 120, w: 26, h: 26, shape: "circle", color: "#fb7185",
          solid: true, tag: "ball", bounce: 0.72 },
      ],
    };
  }

  // ------------------------------------------------------------ input
  class Input {
    constructor(target) {
      this.keys = new Set();
      this.pressed = new Set();     // keys pressed THIS frame
      const down = (e) => {
        const k = this._norm(e);
        if (!k) return;
        if (["arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(k)) {
          e.preventDefault();       // the game owns these keys while playing
        }
        if (!this.keys.has(k)) this.pressed.add(k);
        this.keys.add(k);
      };
      const up = (e) => { const k = this._norm(e); if (k) this.keys.delete(k); };
      target.addEventListener("keydown", down);
      target.addEventListener("keyup", up);
      this._detach = () => {
        target.removeEventListener("keydown", down);
        target.removeEventListener("keyup", up);
      };
    }
    _norm(e) {
      const k = e.key.toLowerCase();
      return { "w": "arrowup", "a": "arrowleft", "d": "arrowright",
               "s": "arrowdown" }[k] || k;
    }
    held(...ks) { return ks.some((k) => this.keys.has(k)); }
    hit(...ks) { return ks.some((k) => this.pressed.has(k)); }
    endFrame() { this.pressed.clear(); }
    dispose() { this._detach(); }
  }

  // ------------------------------------------------------------- game
  class Game {
    constructor(canvas, scene, hooks = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.hooks = hooks;           // {onScore, onHit, onStop}
      this.scene = Game.normalizeScene(scene);
      this.input = new Input(canvas);
      this.running = false;
      this.score = 0;
      this._particles = [];
      this._raf = 0;
      this._last = 0;
      this._acc = 0;
    }

    static normalizeScene(raw) {
      const s = raw && typeof raw === "object" ? raw : {};
      return {
        name: String(s.name || "scene"),
        bg: String(s.bg || "#0b0e1a"),
        gravity: Number(s.gravity ?? 1500),
        camera: Object.assign({ x: 0, y: 0, zoom: 1 }, s.camera || {}),
        entities: (Array.isArray(s.entities) ? s.entities : [])
          .map((e) => makeEntity(e)),
      };
    }

    start() {
      if (this.running) return;
      this.running = true;
      this._last = performance.now();
      this.canvas.focus();
      this.canvas.setAttribute("tabindex", "0");
      const loop = (ts) => {
        if (!this.running) return;
        const dt = Math.min((ts - this._last) / 1000, 1 / 20); // clamp hitches
        this._last = ts;
        this._update(dt);
        this._render();
        this.input.endFrame();
        this._raf = requestAnimationFrame(loop);
      };
      this._raf = requestAnimationFrame(loop);
    }

    stop() {
      this.running = false;
      cancelAnimationFrame(this._raf);
      this.input.dispose();
      if (this.hooks.onStop) this.hooks.onStop(this.score);
    }

    // -------------------------------------------------------- physics
    _aabb(a, b) {
      return a.x < b.x + b.w && a.x + a.w > b.x &&
             a.y < b.y + b.h && a.y + a.h > b.y;
    }

    _update(dt) {
      const cam = this.scene.camera;
      const ents = this.scene.entities.filter((e) => e.alive);
      const solids = ents.filter((e) => e.solid);

      for (const e of ents) {
        // --- controls -------------------------------------------------
        if (e.controls === "platformer") {
          const SPD = 320;
          e.vx = this.input.held("arrowleft") ? -SPD
               : this.input.held("arrowright") ? SPD : 0;
          const grounded = this._grounded(e, solids);
          if (this.input.hit(" ", "arrowup") && grounded) {
            e.vy = -640;
            this._burst(e, "#8b5cf6", 8);
          }
          // fell off the world — respawn at the start
          if (e.y > this._worldBottom() + 400) {
            e.x = 90; e.y = 300; e.vx = e.vy = 0;
            this._flash("ouch — respawned");
          }
        } else if (e.tag === "ball") {
          // demo ball keeps itself company: perpetual gentle bounce
          if (Math.abs(e.vx) < 1) e.vx = 190;
        }

        // --- integrate ------------------------------------------------
        // gravity is OPT-IN per entity: null = dynamic default (things
        // with a controller or a physics tag fall; platforms never do)
        const useGrav = (e.gravity !== null) ? e.gravity
          : (e.controls === "platformer" || e.tag === "ball");
        if (useGrav) e.vy += this.scene.gravity * dt;
        e.x += e.vx * dt;
        this._collideAxis(e, solids, "x");
        e.y += e.vy * dt;
        this._collideAxis(e, solids, "y");

        // world walls (soft): keep things inside the strip
        if (e.x < -260) e.x = -260;
        if (e.x > 1360) e.x = 1360;
      }

      // --- tag events (player -> coin etc.) ---------------------------
      const player = ents.find((e) => e.tag === "player");
      if (player) {
        for (const other of ents) {
          if (other === player || !other.alive || !other.tag) continue;
          if (other.tag === "coin" && this._aabb(player, other)) {
            other.alive = false;
            this.score += 10;
            this._burst(other, other.color, 14);
            if (this.hooks.onScore) this.hooks.onScore(this.score);
          }
        }
        // camera follows the player, softly
        cam.x += ((player.x + player.w / 2) - (cam.x + this.canvas.width / 2)) *
                 Math.min(1, dt * 6);
        cam.y += ((player.y + player.h / 2) - (cam.y + this.canvas.height / 2)) *
                 Math.min(1, dt * 3);
      }

      // --- particles ---------------------------------------------------
      for (const p of this._particles) {
        p.life -= dt;
        p.x += p.vx * dt; p.y += p.vy * dt;
        p.vy += 900 * dt;
      }
      this._particles = this._particles.filter((p) => p.life > 0);
    }

    _grounded(e, solids) {
      const probe = { x: e.x + 2, y: e.y + 2, w: e.w - 4, h: e.h + 3 };
      return solids.some((s) => s !== e && this._aabb(probe, s) && s.y >= e.y);
    }

    _collideAxis(e, solids, axis) {
      for (const s of solids) {
        if (s === e || !s.alive) continue;
        if (!this._aabb(e, s)) continue;
        if (axis === "x") {
          if (e.vx > 0) e.x = s.x - e.w;
          else if (e.vx < 0) e.x = s.x + s.w;
          e.vx = 0;
        } else {
          if (e.vy > 0) {
            e.y = s.y - e.h;
            if (s.bounce) e.vy = -e.vy * s.bounce;
            else if (e.tag === "ball") e.vy = -Math.abs(e.vy) * 0.72;
            else e.vy = 0;
          } else if (e.vy < 0) {
            e.y = s.y + s.h;
            e.vy = 0;
          }
        }
      }
    }

    _worldBottom() {
      return Math.max(...this.scene.entities.map((e) => e.y + e.h), 500);
    }

    // -------------------------------------------------------- effects
    _burst(at, color, n) {
      for (let i = 0; i < n; i++) {
        const a = Math.random() * Math.PI * 2;
        const sp = 90 + Math.random() * 220;
        this._particles.push({
          x: at.x + at.w / 2, y: at.y + at.h / 2,
          vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 120,
          life: 0.35 + Math.random() * 0.3, color,
          size: 2 + Math.random() * 3,
        });
      }
    }

    _flash(text) {
      this._toastText = text;
      this._toastT = 1.6;
    }

    // --------------------------------------------------------- render
    _render() {
      const { ctx, canvas } = this;
      const cam = this.scene.camera;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = this.scene.bg;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // faint parallax stars, so movement reads even in an empty field
      ctx.fillStyle = "rgba(255,255,255,.05)";
      const ox = -cam.x * 0.25, oy = -cam.y * 0.12;
      for (let i = 0; i < 40; i++) {
        const sx = ((i * 173) % canvas.width + ox) % canvas.width;
        const sy = ((i * 97) % canvas.height + oy) % canvas.height;
        ctx.fillRect((sx + canvas.width) % canvas.width,
                     (sy + canvas.height) % canvas.height, 2, 2);
      }

      ctx.save();
      ctx.translate(-cam.x, -cam.y);

      for (const e of this.scene.entities) {
        if (!e.alive) continue;
        if (e.x + e.w < cam.x - 40 || e.x > cam.x + canvas.width + 40) continue;
        ctx.fillStyle = e.color;
        if (e.shape === "circle") {
          ctx.beginPath();
          ctx.arc(e.x + e.w / 2, e.y + e.h / 2, Math.min(e.w, e.h) / 2,
                  0, Math.PI * 2);
          ctx.fill();
          if (e.tag === "coin") {   // coins shimmer
            const t = performance.now() / 300 + e.x;
            ctx.fillStyle = "rgba(255,255,255,.35)";
            ctx.fillRect(e.x + e.w / 2 + Math.cos(t) * e.w / 4,
                         e.y + e.h / 4, 2, e.h / 2);
          }
        } else {
          ctx.beginPath();
          ctx.roundRect(e.x, e.y, e.w, e.h, 5);
          ctx.fill();
          if (e.solid) {           // hairline top light on solids
            ctx.fillStyle = "rgba(255,255,255,.07)";
            ctx.fillRect(e.x, e.y, e.w, 3);
          }
        }
        if (this.selected && this.selected.name === e.name) {
          ctx.strokeStyle = "#22d3ee";
          ctx.lineWidth = 2;
          ctx.strokeRect(e.x - 3, e.y - 3, e.w + 6, e.h + 6);
        }
      }

      for (const p of this._particles) {
        ctx.globalAlpha = Math.max(0, p.life / 0.65);
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x, p.y, p.size, p.size);
      }
      ctx.globalAlpha = 1;
      ctx.restore();

      // HUD
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "rgba(255,255,255,.92)";
      ctx.font = "600 16px ui-monospace, monospace";
      ctx.textBaseline = "top";
      ctx.fillText(`SCORE ${this.score}`, 16, 14);
      const coins = this.scene.entities.filter(
        (e) => e.tag === "coin" && e.alive).length;
      if (coins === 0) {
        ctx.fillStyle = "#34d399";
        ctx.font = "800 26px ui-monospace, monospace";
        ctx.fillText("ALL COINS COLLECTED — you win", 16, 44);
      }
      if (this._toastT > 0) {
        this._toastT -= 1 / 60;
        ctx.fillStyle = "rgba(251,113,133,.95)";
        ctx.font = "600 15px ui-monospace, monospace";
        ctx.fillText(this._toastText, 16, 74);
      }
    }
  }

  return { Game, makeEntity, demoScene };
})();
