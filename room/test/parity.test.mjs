import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runSpec } from "../engine.mjs";

const vectors = JSON.parse(readFileSync(new URL("../../tests/golden/engine_vectors.json", import.meta.url), "utf8"));

for (const c of vectors.cases) {
  test(`parity: ${c.name}`, async () => {
    const got = await runSpec(c.spec);
    assert.equal(got.status, c.expected.status);
    assert.deepEqual(got.decision, c.expected.decision);
    assert.deepEqual(got.entries, c.expected.entries);
    assert.equal(got.transcriptHash, c.expected.transcript_hash);
  });
}
