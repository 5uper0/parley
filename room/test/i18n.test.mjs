import { test } from "node:test";
import assert from "node:assert/strict";
import { T, pickLang } from "../web/i18n.mjs";
import { HEIRS_OPTIONS, PRIORITIES } from "../web/heirs.mjs";

const shape = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) =>
  [k, typeof v === "function" ? v.length : typeof v === "object" ? shape(v) : "s"]));

test("EN and ES carry the same keys, with the same function arity", () => {
  assert.deepEqual(shape(T.es), shape(T.en));
});

test("every option and priority has a label in each language", () => {
  for (const l of ["en", "es"]) {
    for (const o of HEIRS_OPTIONS) assert.ok(T[l].opt[o.id], `${l} opt ${o.id}`);
    for (const p of PRIORITIES) assert.ok(T[l].pri[p], `${l} pri ${p}`);
  }
});

test("no claim the product cannot keep", () => {
  const text = JSON.stringify(T, (k, v) => (typeof v === "function" ? "" : v)).toLowerCase();
  for (const bad of ["secure", "anonymous", "legally binding", "seguro", "anónim", "anonim", "vinculante", "verified by parley"]) {
    assert.ok(!text.includes(bad), bad);
  }
});

test("language pick", () => {
  assert.equal(pickLang({ language: "es-ES" }), "es");
  assert.equal(pickLang({ language: "uk" }), "en");
  assert.equal(pickLang(undefined), "en");
});

import { readFileSync } from "node:fs";
test("Room page: no third-party script, no indexing, no referrer, CSP script-src self", () => {
  const html = readFileSync(new URL("../web/index.html", import.meta.url), "utf8");
  assert.match(html, /name="referrer" content="no-referrer"/);
  assert.match(html, /name="robots" content="noindex/);
  assert.match(html, /Content-Security-Policy[^>]*script-src 'self'/);
  const srcs = [...html.matchAll(/<script[^>]*\ssrc="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(srcs.length > 0 && srcs.every((u) => u.startsWith("./")), `external script: ${srcs}`);
  for (const f of ["app.mjs", "client.mjs", "heirs.mjs", "i18n.mjs"]) {
    const js = readFileSync(new URL(`../web/${f}`, import.meta.url), "utf8");
    assert.ok(!/https?:\/\/(?!wa\.me)/.test(js.replace(/\/\/.*$/gm, "")), `${f} mentions an external URL`);
  }
});
