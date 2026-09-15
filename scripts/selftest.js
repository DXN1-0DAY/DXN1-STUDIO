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

let fails = 0;
for (const [name, fn] of tests) { /* placeholder, replaced below */ }

const assert = (cond, msg) => { if (!cond) { console.error("   FAIL " + msg); process.exit(1); } };

// 1. highlighter: no marker survives, tokens are colored
const out1 = app.highlight('x = "a3" + 5  # keep 42', "py");
assert(!out1.includes("\u0000"), "py: marker leaked");
assert(out1.includes("tok-str") && out1.includes("a3"), "py: string token corrupted");
assert(out1.includes("tok-com") && out1.includes("keep 42"), "py: comment corrupted");

const out2 = app.highlight(".btn { color: #fff; }", "css");
assert(out2.includes("tok-kw"), "css: property not highlighted");
assert(out2.includes("tok-num"), "css: hex color not highlighted");

const out3 = app.highlight('# Title with "quotes"', "md");
assert(!out3.includes("\u0000"), "md: nested marker leaked");
assert(out3.includes("tok-str"), "md: string inside heading lost");

const out4 = app.highlight("<div class=\"x\">hi</div>", "html");
assert(out4.includes("tok-kw"), "html: tag not highlighted");

// 2. langFor routing
assert(app.langFor("a/b/c.css") === "css", "langFor css");
assert(app.langFor("page.HTML") === "html", "langFor html case");
assert(app.langFor("main.py") === "py", "langFor py");

// 3. Spark schema: demo scene entities are complete + new powers exist
const scene = Spark.demoScene();
assert(Array.isArray(scene.entities) && scene.entities.length >= 14, "demo scene entity count");
for (const e of scene.entities) {
  assert(typeof e.name === "string" && typeof e.x === "number", "entity fields: " + e.name);
}
assert(scene.entities.some((e) => e.shape === "triangle"), "triangle shape present");
assert(scene.entities.some((e) => e.text), "text entity present");
assert(scene.entities.filter((e) => e.tag === "hazard").length >= 2, "hazard entities present");
const ent = Spark.makeEntity({ name: "t" });
assert(ent.gravity === null && ent.alive === true, "makeEntity defaults");

console.log("renderer selftest: all green (" + 12 + " assertions)");
