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
  // entity: {name, x, y, w, h, shape:"rect"|"circle"|"triangle",
  //          color, color2, fill:"solid"|"gradient", rot:degrees,
  //          text:"", tsize:22,
  //          vx, vy, solid, gravity:boolean(default: scene gravity),
  //          controls:"platformer"|"none", tag, bounce:0..1, alive:true,
  //          path:null|{toX,toY,speed} — moving platform, ping-pong}
  //          tag:"coin" pickup · tag:"hazard" respawn on touch
  //          tag:"goal" finish — sends the player to scene.next
  //          rot is VISUAL — physics stays an honest AABB
  // scene:  {name, bg, gravity, camera:{x,y,zoom}, entities:[...],
  //          next:null|"scenes/level2.dxn1.json", parallax:[{speed,color,size,count}]}

  function makeEntity(patch) {
    return Object.assign({
      name: "entity", x: 0, y: 0, w: 36, h: 36,
      shape: "rect", color: "#8b5cf6", color2: "", fill: "solid",
      rot: 0, spin: 0, text: "", tsize: 22,
      vx: 0, vy: 0, solid: false, gravity: null,
      controls: "none", tag: "", bounce: 0, alive: true,
      path: null,
    }, patch || {});
  }

  function demoScene() {
    return {
      name: "playground",
      bg: "#0b0e1a",
      gravity: 1500,
      magnet: 110,          // coins drift toward the player inside this radius
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
        { name: "spike-1", x: 470, y: 402, w: 34, h: 28, shape: "triangle",
          color: "#fb7185", tag: "hazard" },
        { name: "spike-2", x: 740, y: 402, w: 34, h: 28, shape: "triangle",
          color: "#fb7185", tag: "hazard" },
        { name: "sign", x: 130, y: 360, w: 190, h: 30, text: "→ find the coins",
          tsize: 20, color: "#9aa1b5" },
        { name: "sign-2", x: 1080, y: 300, w: 150, h: 30, text: "goal →",
          tsize: 20, color: "#9aa1b5" },
        { name: "goal", x: 1250, y: 366, w: 30, h: 64, color: "#34d399",
          tag: "goal" },
      ],
      next: "scenes/level-2.dxn1.json",
    };
  }

  // level 2 — moving platforms are the whole point here
  function demoScene2() {
    return {
      name: "level-2",
      bg: "#0d0b1c",
      gravity: 1500,
      magnet: 140,          // bigger magnet — the movers make you earn it
      camera: { x: 0, y: 0, zoom: 1 },
      entities: [
        { name: "player", x: 80, y: 330, w: 34, h: 44, color: "#8b5cf6",
          controls: "platformer", solid: true, tag: "player" },
        { name: "ground-a", x: -200, y: 430, w: 560, h: 90, color: "#1c2136", solid: true },
        { name: "ground-b", x: 760, y: 430, w: 700, h: 90, color: "#1c2136", solid: true },
        { name: "mover-1", x: 400, y: 360, w: 150, h: 22, color: "#22d3ee",
          solid: true, path: { toX: 660, toY: 250, speed: 110 } },
        { name: "mover-2", x: 980, y: 300, w: 130, h: 22, color: "#22d3ee",
          solid: true, path: { toX: 1130, toY: 300, speed: 90 } },
        { name: "coin-1", x: 560, y: 190, w: 22, h: 22, shape: "circle", color: "#fbbf24", tag: "coin" },
        { name: "coin-2", x: 1030, y: 240, w: 22, h: 22, shape: "circle", color: "#fbbf24", tag: "coin" },
        { name: "spike-1", x: 880, y: 402, w: 34, h: 28, shape: "triangle",
          color: "#fb7185", tag: "hazard" },
        { name: "saw", x: 640, y: 396, w: 38, h: 38, color: "#fb7185",
          tag: "hazard", rot: 0, spin: 260 },
        { name: "sign", x: 90, y: 360, w: 210, h: 30, text: "ride the movers!",
          tsize: 20, color: "#9aa1b5" },
        { name: "goal", x: 1330, y: 366, w: 30, h: 64, color: "#34d399",
          tag: "goal" },
      ],
      next: "scenes/playground.dxn1.json",
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

  // ------------------------------------------------------------ audio
  // tiny synth — no assets, no network, just honest bleeps
  class Sfx {
    constructor(volume = 0.5) { this.vol = volume; this.ctx = null; }
    ensure() {
      if (this.vol <= 0) return null;
      if (!this.ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        this.ctx = new AC();
      }
      if (this.ctx.state === "suspended") this.ctx.resume();
      return this.ctx;
    }
    tone(freq, dur, type = "square", vol = 1, slide = 0) {
      const ac = this.ensure();
      if (!ac) return;
      const t = ac.currentTime;
      const o = ac.createOscillator(), g = ac.createGain();
      o.type = type;
      o.frequency.setValueAtTime(freq, t);
      if (slide) {
        o.frequency.exponentialRampToValueAtTime(
          Math.max(40, freq + slide), t + dur);
      }
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.22 * this.vol * vol, t + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      o.connect(g); g.connect(ac.destination);
      o.start(t); o.stop(t + dur + 0.02);
    }
    jump()   { this.tone(240, 0.14, "square", 0.8, 260); }
    coin()   { this.tone(880, 0.09, "square", 0.7);
               setTimeout(() => this.tone(1320, 0.12, "square", 0.7), 70); }
    hit()    { this.tone(220, 0.22, "sawtooth", 0.9, -140); }
    bounce() { this.tone(140, 0.08, "triangle", 0.6, 60); }
    goal()   { [523, 659, 784, 1047].forEach((f, i) =>
               setTimeout(() => this.tone(f, 0.16, "triangle", 0.8), i * 110)); }
  }

  // ------------------------------------------------------------- game
  class Game {
    constructor(canvas, scene, hooks = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.hooks = hooks;           // {onScore, onHit, onTransition, onStop}
      this.sfx = new Sfx(hooks.volume ?? 0.5);
      this.scene = Game.normalizeScene(scene);
      this.input = new Input(canvas);
      this.running = false;
      this.score = 0;
      this._time = 0;              // seconds since start()
      this._transLock = false;     // one goal trigger per attempt
      this.showGrid = false;          // editor-only overlay
      this.gridSize = 32;
      this._particles = [];
      this._raf = 0;
      this._last = 0;
      this._acc = 0;
      this._shakeT = 0;            // camera shake — seconds left
      this._shakeP = 0;            // …and its power (px)
      this._shakeD = 1;            // …and the duration it decays over
      this._sounds = [];           // sound events this frame (QA-able)
      const pl = this.scene.entities.find((e) => e.tag === "player");
      this._spawn = { x: pl ? pl.x : 90, y: pl ? pl.y : 300 };
    }

    /* one static frame — the editor paints through this */
    repaint() { this._render(); }

    static normalizeScene(raw) {
      const s = raw && typeof raw === "object" ? raw : {};
      const cam = Object.assign({ x: 0, y: 0, zoom: 1 }, s.camera || {});
      return {
        name: String(s.name || "scene"),
        bg: String(s.bg || "#0b0e1a"),
        gravity: Number(s.gravity ?? 1500),
        magnet: Math.max(0, Number(s.magnet) || 0),  // coin magnet radius, px
        camera: { x: Number(cam.x) || 0, y: Number(cam.y) || 0,
                  zoom: Math.min(4, Math.max(0.3, Number(cam.zoom) || 1)) },
        entities: (Array.isArray(s.entities) ? s.entities : [])
          .map((e) => makeEntity(e)),
        next: typeof s.next === "string" ? s.next : null,
        parallax: Game._normalizeParallax(s.parallax),
      };
    }

    static _normalizeParallax(p) {
      if (Array.isArray(p) && p.length) {
        return p.map((l) => ({
          speed: Math.max(0, Math.min(1, Number(l.speed) || 0.25)),
          color: String(l.color || "rgba(255,255,255,.05)"),
          size: Math.max(1, Number(l.size) || 2),
          count: Math.max(1, Math.min(400, Number(l.count) || 40)),
        }));
      }
      // the classic star field stays the default
      return [{ speed: 0.25, color: "rgba(255,255,255,.05)", size: 2, count: 40 }];
    }

    // -------------------------------------------------- editor helpers
    // camera shake — cosmetic only, never touches the camera itself
    shake(power = 8, dur = 0.35) {
      this._shakeP = Math.max(0, Math.min(40, Number(power) || 0));
      this._shakeD = Math.max(0.05, Number(dur) || 0.05);
      this._shakeT = this._shakeD;
    }

    screenToWorld(sx, sy) {
      const cam = this.scene.camera;
      const r = this.canvas.getBoundingClientRect();
      const scale = this.canvas.width / r.width;   // CSS → backing pixels
      const z = cam.zoom || 1;
      return { x: (sx - r.left) * scale / z + cam.x,
               y: (sy - r.top) * scale / z + cam.y };
    }

    // editor zoom — keep the world point under the cursor fixed
    zoomAt(factor, sx, sy) {
      const cam = this.scene.camera;
      const before = this.screenToWorld(sx, sy);
      cam.zoom = Math.min(4, Math.max(0.3, (cam.zoom || 1) * factor));
      const after = this.screenToWorld(sx, sy);
      cam.x += before.x - after.x;
      cam.y += before.y - after.y;
    }

    zoomFit() {
      const cam = this.scene.camera;
      cam.zoom = 1; cam.x = 0; cam.y = 0;
      if (!this.running) this.repaint();
    }

    entityAt(wx, wy) {
      for (let i = this.scene.entities.length - 1; i >= 0; i--) {
        const e = this.scene.entities[i];
        if (!e.alive) continue;
        if (wx >= e.x && wx <= e.x + e.w && wy >= e.y && wy <= e.y + e.h) {
          return e;
        }
      }
      return null;
    }

    start() {
      if (this.running) return;
      this.running = true;
      // play from where the editor left the player
      const pl0 = this.scene.entities.find((e) => e.tag === "player");
      if (pl0) this._spawn = { x: pl0.x, y: pl0.y };
      this._time = 0;
      this._transLock = false;
      // movers launch from wherever the editor left them
      for (const e of this.scene.entities) {
        if (e.path) { e._home = { x: e.x, y: e.y }; e._pt = 0; e._pd = 1; }
      }
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
      this._time += dt;
      this._movePaths(dt, ents);

      for (const e of ents) {
        if (e.spin) e.rot = ((e.rot || 0) + e.spin * dt) % 360;
        // --- controls -------------------------------------------------
        if (e.controls === "platformer") {
          const SPD = 320;
          e.vx = this.input.held("arrowleft") ? -SPD
               : this.input.held("arrowright") ? SPD : 0;
          const grounded = this._grounded(e, solids);
          if (this.input.hit(" ", "arrowup") && grounded) {
            e.vy = -640;
            this._burst(e, "#8b5cf6", 8);
            this.sfx.jump();
          }
          // fell off the world — respawn at the start
          if (e.y > this._worldBottom() + 400) {
            e.x = this._spawn.x; e.y = this._spawn.y; e.vx = e.vy = 0;
            this._flash("ouch — respawned");
            this.shake(6, 0.3);
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
      // camera shake decays with time, not frames
      if (this._shakeT > 0) this._shakeT = Math.max(0, this._shakeT - dt);

      const player = ents.find((e) => e.tag === "player");
      if (player) {
        // coin magnetism — scene.magnet radius; pull grows as coins close in
        const mag = this.scene.magnet || 0;
        if (mag > 0) {
          const pcx = player.x + player.w / 2, pcy = player.y + player.h / 2;
          for (const c of ents) {
            if (c.tag !== "coin" || !c.alive) continue;
            const dx = pcx - (c.x + c.w / 2), dy = pcy - (c.y + c.h / 2);
            const d = Math.hypot(dx, dy);
            if (d < mag && d > 1) {
              const pull = (1 - d / mag) * 360 * dt;   // stronger when closer
              c.x += (dx / d) * pull;
              c.y += (dy / d) * pull;
              c._mag = true;
            } else c._mag = false;
          }
        }
        for (const other of ents) {
          if (other === player || !other.alive || !other.tag) continue;
          if (other.tag === "coin" && this._aabb(player, other)) {
            other.alive = false;
            this.score += 10;
            this._burst(other, other.color, 14);
            this.sfx.coin();
            if (this.hooks.onScore) this.hooks.onScore(this.score);
          }
          if (other.tag === "hazard" && this._aabb(player, other)) {
            this._burst(player, "#fb7185", 16);
            player.x = this._spawn.x; player.y = this._spawn.y;
            player.vx = player.vy = 0;
            this._flash("ouch — spike!");
            this.sfx.hit();
            this.shake(10, 0.4);
            if (this.hooks.onHit) this.hooks.onHit();
          }
          if (other.tag === "goal" && !this._transLock &&
              this._aabb(player, other)) {
            this._transLock = true;
            this._burst(player, "#34d399", 24);
            this._flash(this.scene.next ? "LEVEL CLEAR!" : "GOAL! — you win");
            this.sfx.goal();
            this.shake(4, 0.25);
            if (this.hooks.onTransition) {
              this.hooks.onTransition(this.scene.next, this);
            }
          }
        }
        // camera follows the player, softly (center of the zoomed view)
        const z = cam.zoom || 1;
        cam.x += ((player.x + player.w / 2) - (cam.x + this.canvas.width / (2 * z))) *
                 Math.min(1, dt * 6);
        cam.y += ((player.y + player.h / 2) - (cam.y + this.canvas.height / (2 * z))) *
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
            if (s.bounce) {
              e.vy = -e.vy * s.bounce;
              if (e.vy > 120) this.sfx.bounce();   // no machine-gun thuds
            } else if (e.tag === "ball") {
              e.vy = -Math.abs(e.vy) * 0.72;
              if (e.vy > 120) this.sfx.bounce();
            } else e.vy = 0;
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

    // -------------------------------------------------- moving platforms
    _movePaths(dt, ents) {
      for (const e of ents) {
        const p = e.path;
        if (!p || !e._home) continue;
        const ax = Number(p.toX) || 0, ay = Number(p.toY) || 0;
        const len = Math.hypot(ax - e._home.x, ay - e._home.y);
        if (len < 1) continue;
        const speed = Math.max(1, Number(p.speed) || 120);
        let t = (e._pt || 0) + (e._pd || 1) * speed * dt / len;
        if (t >= 1) { t = 1; e._pd = -1; }
        else if (t <= 0) { t = 0; e._pd = 1; }
        e._pt = t;
        const ox = e.x, oy = e.y;
        e.x = e._home.x + (ax - e._home.x) * t;
        e.y = e._home.y + (ay - e._home.y) * t;
        // carry whatever stands on the old top
        for (const r of ents) {
          if (r === e || !r.alive || r.path) continue;
          const dynamic = r.gravity === true || (r.gravity === null &&
            (r.controls === "platformer" || r.tag === "ball"));
          if (!dynamic || r.vy < 0) continue;
          const bottom = r.y + r.h;
          if (r.x + r.w > ox + 2 && r.x < ox + e.w - 2 &&
              bottom >= oy - 12 && bottom <= oy + 8) {
            r.x += e.x - ox;
            r.y = e.y - r.h;
          }
        }
      }
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
      const z = cam.zoom || 1;
      const wrap = (v, m) => ((v % m) + m) % m;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = this.scene.bg;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // parallax layers — configurable per scene, stars by default
      for (const L of (this.scene.parallax || [])) {
        ctx.fillStyle = L.color;
        const ox = -cam.x * L.speed, oy = -cam.y * L.speed * 0.5;
        for (let i = 0; i < L.count; i++) {
          const sx = wrap(i * 173, canvas.width) + ox;
          const sy = wrap(i * 97, canvas.height) + oy;
          ctx.fillRect(wrap(sx, canvas.width), wrap(sy, canvas.height),
                       L.size, L.size);
        }
      }

      ctx.save();
      ctx.scale(z, z);
      // shake offset — random jitter scaled by remaining fraction of duration
      let shx = 0, shy = 0;
      if (this._shakeT > 0 && this.running) {
        const k = this._shakeP * (this._shakeT / this._shakeD);
        shx = (Math.random() * 2 - 1) * k;
        shy = (Math.random() * 2 - 1) * k;
      }
      ctx.translate(-cam.x + shx, -cam.y + shy);
      const viewW = canvas.width / z, viewH = canvas.height / z;

      // editor grid — only while editing (the game never sees it)
      if (this.showGrid && !this.running) {
        const gs = this.gridSize || 32;
        ctx.strokeStyle = "rgba(139,92,246,.14)";
        ctx.lineWidth = 1 / z;
        ctx.beginPath();
        for (let x = Math.floor(cam.x / gs) * gs;
             x <= cam.x + viewW + gs; x += gs) {
          ctx.moveTo(x, cam.y); ctx.lineTo(x, cam.y + viewH);
        }
        for (let y = Math.floor(cam.y / gs) * gs;
             y <= cam.y + viewH + gs; y += gs) {
          ctx.moveTo(cam.x, y); ctx.lineTo(cam.x + viewW, y);
        }
        ctx.stroke();
      }

      for (const e of this.scene.entities) {
        if (!e.alive) continue;
        if (e.x + e.w < cam.x - 40 || e.x > cam.x + viewW + 40) continue;
        if (e.text) {                 // text entity — drawn as a label
          ctx.fillStyle = e.color;
          ctx.font = `600 ${e.tsize || 22}px ui-monospace, monospace`;
          ctx.textBaseline = "top";
          ctx.fillText(e.text, e.x, e.y);
        } else if (e.shape === "circle") {
          ctx.beginPath();
          ctx.arc(e.x + e.w / 2, e.y + e.h / 2, Math.min(e.w, e.h) / 2,
                  0, Math.PI * 2);
          ctx.fill();
          if (e.tag === "coin") {   // coins shimmer
            const t = performance.now() / 300 + e.x;
            ctx.fillStyle = "rgba(255,255,255,.35)";
            ctx.fillRect(e.x + e.w / 2 + Math.cos(t) * e.w / 4,
                         e.y + e.h / 4, 2, e.h / 2);
            if (e._mag) {            // magnetized — ring tell
              ctx.strokeStyle = "rgba(251,191,36,.8)";
              ctx.lineWidth = 1.5 / z;
              ctx.beginPath();
              ctx.arc(e.x + e.w / 2, e.y + e.h / 2,
                      Math.min(e.w, e.h) / 2 + 4 / z, 0, Math.PI * 2);
              ctx.stroke();
            }
          }
        } else if (e.shape === "triangle") {
          const drawTri = (px, py) => {
            ctx.beginPath();
            ctx.moveTo(px + e.w / 2, py);
            ctx.lineTo(px + e.w, py + e.h);
            ctx.lineTo(px, py + e.h);
            ctx.closePath();
            ctx.fill();
          };
          if (e.rot) {
            ctx.save();
            ctx.translate(e.x + e.w / 2, e.y + e.h / 2);
            ctx.rotate(e.rot * Math.PI / 180);
            drawTri(-e.w / 2, -e.h / 2);
            ctx.restore();
          } else drawTri(e.x, e.y);
        } else {
          const drawRect = (px, py) => {
            ctx.beginPath();
            ctx.roundRect(px, py, e.w, e.h, 5);
            ctx.fill();
            if (e.solid) {           // hairline top light on solids
              ctx.fillStyle = "rgba(255,255,255,.07)";
              ctx.fillRect(px, py, e.w, 3);
            }
          };
          if (e.rot) {
            ctx.save();
            ctx.translate(e.x + e.w / 2, e.y + e.h / 2);
            ctx.rotate(e.rot * Math.PI / 180);
            drawRect(-e.w / 2, -e.h / 2);
            ctx.restore();
          } else drawRect(e.x, e.y);
        }
        if (e.path && !this.running) {   // motion rail — editors deserve it
          ctx.strokeStyle = "rgba(34,211,238,.35)";
          ctx.lineWidth = 1.5 / z;
          ctx.setLineDash([6 / z, 5 / z]);
          ctx.beginPath();
          ctx.moveTo(e._home ? e._home.x : e.x, e._home ? e._home.y : e.y);
          ctx.lineTo(e.path.toX, e.path.toY);
          ctx.stroke();
          ctx.setLineDash([]);
        }
        if (this.selected && this.selected === e) {   // identity, not name
          ctx.strokeStyle = "#22d3ee";
          ctx.lineWidth = 2 / z;
          ctx.strokeRect(e.x - 3 / z, e.y - 3 / z, e.w + 6 / z, e.h + 6 / z);
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
      const tm = Math.floor((this._time || 0) / 60);
      const ts = ((this._time || 0) % 60).toFixed(1).padStart(4, "0");
      ctx.fillText(`SCORE ${this.score}   TIME ${tm}:${ts}`, 16, 14);
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

  return { Game, makeEntity, demoScene, demoScene2, Sfx };
})();
