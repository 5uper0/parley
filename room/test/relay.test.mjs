import { test } from "node:test";
import assert from "node:assert/strict";
import { createRoom, join, submit, publicRoom, verdictPayload, RelayError } from "../relay/core.mjs";
import { verdictFor } from "../engine.mjs";

const OPTIONS = [{ slot: "sat" }, { slot: "sun" }];
const SHEETS = {
  ana: { owner: "ana", hard: [{ attr: "slot", op: "!=", value: "sun" }], utility: [] },
  ben: { owner: "ben", hard: [], utility: [{ attr: "slot", prefer: "sat", weight: 1 }] },
};

async function device(owner) {
  const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  const raw = new Uint8Array(await crypto.subtle.exportKey("raw", kp.publicKey));
  return { kp, pub: Array.from(raw, (b) => b.toString(16).padStart(2, "0")).join(""), owner };
}
async function answer(room, dev, sheet = SHEETS[dev.owner]) {
  return Promise.all(room.options.map(async (option, i) => {
    const v = verdictFor(sheet, option);
    const payload = verdictPayload({ option, owner: dev.owner, acceptable: v.acceptable, score: v.score,
      reason: v.reason, session: room.session, nonce: room.nonces[dev.owner][i] });
    const sig = Array.from(new Uint8Array(await crypto.subtle.sign({ name: "Ed25519" }, dev.kp.privateKey, payload)),
      (b) => b.toString(16).padStart(2, "0")).join("");
    return { acceptable: v.acceptable, score: v.score, reason: v.reason, sig };
  }));
}
const code = async (p) => { try { await p; } catch (e) { assert.ok(e instanceof RelayError); return e.code; } return "no-error"; };

test("two devices agree, record carries signatures", async () => {
  const room = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const [a, b] = [await device("ana"), await device("ben")];
  join(room, "ana", a.pub, room.tokens["ana"]); join(room, "ben", b.pub, room.tokens["ben"]);
  await submit(room, "ana", await answer(room, a));
  assert.equal(room.result, null);
  await submit(room, "ben", await answer(room, b));
  assert.equal(room.result.status, "agreed");
  assert.deepEqual(room.result.decision, { slot: "sat" });
  assert.match(room.result.transcript_hash, /^[0-9a-f]{64}$/);
});

test("honest deadlock when red lines leave nothing", async () => {
  const room = createRoom({ options: [{ slot: "sun" }], owners: ["ana", "ben"] });
  const [a, b] = [await device("ana"), await device("ben")];
  join(room, "ana", a.pub, room.tokens["ana"]); join(room, "ben", b.pub, room.tokens["ben"]);
  await submit(room, "ana", await answer(room, a));
  await submit(room, "ben", await answer(room, b));
  assert.equal(room.result.status, "deadlock");
});

test("public view never holds sheets or other people's verdicts", async () => {
  const room = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const a = await device("ana"); join(room, "ana", a.pub, room.tokens["ana"]);
  await submit(room, "ana", await answer(room, a));
  const view = JSON.stringify(publicRoom(room));
  assert.ok(!view.includes("red-line") && !view.includes("score") && !view.includes("sig"));
});

test("R1: one key per owner, one owner per key, unknown owner refused", async () => {
  const room = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const [a, b] = [await device("ana"), await device("ben")];
  join(room, "ana", a.pub, room.tokens["ana"]);
  assert.equal(await code(Promise.resolve().then(() => join(room, "ana", b.pub, room.tokens["ana"]))), "already-joined");
  assert.equal(await code(Promise.resolve().then(() => join(room, "ben", a.pub, room.tokens["ben"]))), "key-reused");
  assert.equal(await code(Promise.resolve().then(() => join(room, "eve", b.pub, room.tokens["eve"]))), "unknown-owner");
  assert.equal(await code(Promise.resolve().then(() => join(room, "ben", "zz", room.tokens.ben))), "bad-key");
});

test("R2: verdict signed for another session is refused", async () => {
  const r1 = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const r2 = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const a = await device("ana"); join(r1, "ana", a.pub, r1.tokens["ana"]); join(r2, "ana", a.pub, r2.tokens["ana"]);
  assert.equal(await code(submit(r2, "ana", await answer(r1, a))), "bad-signature");
});

test("a tampered score, flipped acceptable or foreign key fails signature", async () => {
  const room = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const [a, b] = [await device("ana"), await device("ben")];
  join(room, "ana", a.pub, room.tokens["ana"]); join(room, "ben", b.pub, room.tokens["ben"]);
  const good = await answer(room, a);
  assert.equal(await code(submit(room, "ana", good.map((v, i) => i ? v : { ...v, score: 1 }))), "bad-signature");
  assert.equal(await code(submit(room, "ana", good.map((v) => v.acceptable ? v : { ...v, score: 0.3 }))), "bad-verdicts"); // a red-line verdict must carry 0
  assert.equal(await code(submit(room, "ana", await answer(room, b, SHEETS.ana))), "bad-signature");
});

test("malformed verdicts and double submit refused; no values in error", async () => {
  const room = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const a = await device("ana"); join(room, "ana", a.pub, room.tokens["ana"]);
  const good = await answer(room, a);
  assert.equal(await code(submit(room, "ana", good.slice(0, 1))), "bad-verdicts");
  assert.equal(await code(submit(room, "ana", good.map((v) => ({ ...v, score: 2 })))), "bad-verdicts");
  assert.equal(await code(submit(room, "ana", good.map((v) => ({ ...v, reason: "x" })))), "bad-verdicts");
  assert.equal(await code(submit(room, "ben", good)), "not-joined");
  await submit(room, "ana", good);
  assert.equal(await code(submit(room, "ana", good)), "already-submitted");
});

test("room setup rejects duplicate options, one owner, non-objects", () => {
  assert.throws(() => createRoom({ options: [{ a: 1 }, { a: 1 }], owners: ["a", "b"] }), RelayError);
  assert.throws(() => createRoom({ options: OPTIONS, owners: ["a"] }), RelayError);
  assert.throws(() => createRoom({ options: [1], owners: ["a", "b"] }), RelayError);
});

import { rateAllow, BAD_LIMIT, BAD_WINDOW_MS } from "../relay/core.mjs";

test("P2: one owner is slowed after repeated bad submissions, others and later time are not", async () => {
  const room = createRoom({ options: OPTIONS, owners: ["ana", "ben"] });
  const [a, b] = [await device("ana"), await device("ben")];
  join(room, "ana", a.pub, room.tokens["ana"]); join(room, "ben", b.pub, room.tokens["ben"]);
  const good = await answer(room, a);
  const bad = good.map((v) => ({ ...v, score: 1 }));
  const t0 = 1_000_000;
  for (let i = 0; i < BAD_LIMIT; i++) assert.equal(await code(submit(room, "ana", bad, t0 + i)), "bad-signature");
  assert.equal(await code(submit(room, "ana", good, t0 + 10)), "locked");
  await submit(room, "ben", await answer(room, b), t0 + 10);              // ben unaffected
  await submit(room, "ana", good, t0 + BAD_WINDOW_MS + BAD_LIMIT + 1);    // ana recovers after the window
  assert.equal(room.result.status, "agreed");
});

test("P2: sliding-window limiter", () => {
  let s = [];
  for (let i = 0; i < 3; i++) s = rateAllow(s, 1000 + i, 3, 10_000);
  assert.equal(rateAllow(s, 2000, 3, 10_000), null);
  assert.ok(rateAllow(s, 20_000, 3, 10_000));
});
