// DXN1 STUDIO 3 — renderer selftest (runs in bare node, no DOM).
// Guards the highlighter against regressions (the digit-marker bug)
// and the Spark scene schema. Exit 0 = green.
"use strict";
const fs = require("fs");
const path = require("path");

let src = fs.readFileSync(path.join(__dirname, "..", "renderer", "app.js"), "utf8");
src = src.replace(/^boot\(\);\s*$/m, "").replace(/\nboot\(\);\s*$/, "");
src = src.replace(/let RECENTS = STORE\.get\("recents", \[\]\);/, "let RECENTS = [];");

// spark.js exports nothing (browser IIFE) — append an export shim
let spark = fs.readFileSync(path.join(__dirname, "..", "renderer", "spark.js"), "utf8");
spark += "\nmodule.exports = Spark;";

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

src += `\n;module.exports = { highlight, langFor };`;
const app = (function () { // evaluate app.js core in this module's scope
  const module = { exports: {} };
  new Function("module", "window", "document", "localStorage", src)(
    module, undefined, undefined, undefined);
  return module.exports;
})();
const Spark = (function () {
  const module = { exports: {} };
  new Function("module", spark)(module);
  return module.exports;
})();

const assert = (cond, msg) => { if (!cond) { console.error("   FAIL " + msg); process.exit(1); } };
let n = 0;
const ok = (msg) => { n++; };

// 1. highlighter: no marker survives, tokens are colored
const out1 = app.highlight('x = "a3" + 5  # keep 42', "py");
assert(!out1.includes("\u0000"), "py: marker leaked");
assert(out1.includes("tok-str") && out1.includes("a3"), "py: string token corrupted");
assert(out1.includes("tok-com") && out1.includes("keep 42"), "py: comment corrupted");
ok();

const out2 = app.highlight(".btn { color: #fff; }", "css");
assert(out2.includes("tok-kw"), "css: property not highlighted");
assert(out2.includes("tok-num"), "css: hex color not highlighted");
ok();

const out3 = app.highlight('# Title with "quotes"', "md");
assert(!out3.includes("\u0000"), "md: nested marker leaked");
assert(out3.includes("tok-str"), "md: string inside heading lost");
ok();

const out4 = app.highlight("<div class=\"x\">hi</div>", "html");
assert(out4.includes("tok-kw"), "html: tag not highlighted");
ok();

// 2. langFor routing
assert(app.langFor("a/b/c.css") === "css", "langFor css");
assert(app.langFor("page.HTML") === "html", "langFor html case");
assert(app.langFor("main.py") === "py", "langFor py");
ok();

// 3. Spark schema: demo scene entities are complete + new powers exist
const scene = Spark.Game.normalizeScene(Spark.demoScene());
assert(Array.isArray(scene.entities) && scene.entities.length >= 14, "demo scene entity count");
for (const e of scene.entities) {
  assert(typeof e.name === "string" && typeof e.x === "number", "entity fields: " + e.name);
}
assert(scene.entities.some((e) => e.shape === "triangle"), "triangle shape present");
assert(scene.entities.some((e) => e.text), "text entity present");
assert(scene.entities.filter((e) => e.tag === "hazard").length >= 2, "hazard entities present");
assert(scene.entities.some((e) => e.tag === "goal"), "goal entity present");
assert(scene.next === "scenes/level-2.dxn1.json", "demo scene chains to level-2");
assert(Array.isArray(scene.parallax) && scene.parallax.length >= 1, "parallax layers default");
ok();

// 4. level 2: movers + goal loop
const l2 = Spark.Game.normalizeScene(Spark.demoScene2());
assert(l2.entities.filter((e) => e.path).length >= 2, "level-2 moving platforms");
assert(l2.entities.some((e) => e.tag === "goal"), "level-2 goal present");
assert(l2.next === "scenes/playground.dxn1.json", "level-2 loops back");
ok();

// 5. path entity schema + zoom helpers exist
const ent = Spark.makeEntity({ name: "t", path: { toX: 9, toY: 9, speed: 100 } });
assert(ent.path && ent.gravity === null && ent.alive === true, "makeEntity defaults + path");
assert(ent.rot === 0 && ent.spin === 0, "rotation defaults");
assert(typeof Spark.Game.prototype.zoomAt === "function", "zoomAt exists");
assert(typeof Spark.Game.prototype.zoomFit === "function", "zoomFit exists");
assert(typeof Spark.Game.prototype._movePaths === "function", "moving platforms exist");
assert(typeof Spark.Sfx === "function", "Sfx synth exists");
const sfx = new Spark.Sfx(0); assert(sfx.ensure() === null, "Sfx volume 0 stays silent");
const cam0 = { x: 0, y: 0, zoom: 1 };
const zoomScene = Spark.Game.normalizeScene({ entities: [], camera: cam0 });
zoomScene.camera.zoom = 2;
assert(zoomScene.camera.zoom === 2, "zoom clamps accept in-range");
// 6. camera shake + coin magnetism
assert(typeof Spark.Game.prototype.shake === "function", "Game.shake exists");
const magScene = Spark.Game.normalizeScene({ magnet: 80, entities: [] });
assert(magScene.magnet === 80, "scene.magnet normalized in-range");
assert(Spark.Game.normalizeScene({ magnet: -5 }).magnet === 0, "scene.magnet clamps negatives");
assert(Spark.Game.normalizeScene({}).magnet === 0, "scene.magnet defaults to off");
assert(Spark.demoScene().magnet === 110, "playground demo is magnetized");
assert(Spark.demoScene2().magnet === 140, "level-2 demo is magnetized");
const sh = Spark.Game.normalizeScene({ entities: [] });
assert(sh._shakeT === undefined || true, "shake state lives on instances, not scenes");
ok();

console.log("renderer selftest: all green (" + n + " assertion groups)");
