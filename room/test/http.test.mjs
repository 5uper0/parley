import { test } from "node:test";
import assert from "node:assert/strict";
import { handle, serialHandler } from "../relay/http.mjs";
import { verdictPayload } from "../relay/core.mjs";
import { verdictFor } from "../engine.mjs";

const mkStore = () => { let r; return { get: async () => r && structuredClone(r), put: async (x) => { r = structuredClone(x); } }; };
const req = (method, body) => new Request("https://x/rooms/a", { method, body: body === undefined ? undefined : JSON.stringify(body) });
const hex = (b) => Array.from(new Uint8Array(b), (x) => x.toString(16).padStart(2, "0")).join("");

test("full flow over HTTP, errors carry codes only", async () => {
  const s = mkStore();
  const options = [{ slot: "sat" }, { slot: "sun" }];
  let r = await handle(req("POST", { options, owners: ["ana", "ben"] }), "", s);
  assert.equal(r.status, 201);
  const pub = await r.json();
  assert.equal((await handle(req("POST", { options, owners: ["ana", "ben"] }), "", s)).status, 409);
  assert.equal((await handle(req("GET"), "/result", s)).status, 425);
  const sheets = { ana: { owner: "ana", hard: [], utility: [] }, ben: { owner: "ben", hard: [{ attr: "slot", op: "==", value: "sat" }], utility: [] } };
  for (const owner of ["ana", "ben"]) {
    const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    r = await handle(req("POST", { owner, pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)) }), "/join", s);
    const { session, nonces } = await r.json();
    const verdicts = [];
    for (let i = 0; i < options.length; i++) {
      const v = verdictFor(sheets[owner], options[i]);
      const sig = hex(await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey,
        verdictPayload({ option: options[i], owner, ...v, session, nonce: nonces[i] })));
      verdicts.push({ acceptable: v.acceptable, score: v.score, reason: v.reason, sig });
    }
    r = await handle(req("POST", { owner, verdicts }), "/verdicts", s);
    assert.equal(r.status, 200);
  }
  const res = await (await handle(req("GET"), "/result", s)).json();
  assert.equal(res.status, "agreed");
  assert.deepEqual(res.decision, { slot: "sat" });
  const bad = await handle(req("POST", { owner: "ana", verdicts: [] }), "/verdicts", s);
  assert.equal(bad.status, 409);
  assert.deepEqual(await bad.json(), { error: "room-closed" });
});

test("bad json, oversize body, unknown path, no room", async () => {
  const s = mkStore();
  assert.equal((await handle(new Request("https://x/", { method: "POST", body: "{" }), "", s)).status, 400);
  assert.equal((await handle(new Request("https://x/", { method: "POST", body: "x".repeat(70000) }), "", s)).status, 400);
  assert.equal((await handle(req("GET"), "", s)).status, 404);
});

test("P2: bad-attempt count survives failed requests; locked answers 429", async () => {
  const s = mkStore();
  const options = [{ slot: "sat" }];
  await handle(req("POST", { options, owners: ["ana", "ben"] }), "", s);
  const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  await handle(req("POST", { owner: "ana", pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)) }), "/join", s);
  const junk = [{ acceptable: true, score: 0.5, reason: "ok", sig: "0".repeat(128) }];
  let last;
  for (let i = 0; i < 6; i++) last = await handle(req("POST", { owner: "ana", verdicts: junk }), "/verdicts", s);
  assert.equal(last.status, 429);
  assert.deepEqual(await last.json(), { error: "locked" });
});

test("P2: overlapping requests do not overwrite each other (serialHandler)", async () => {
  let stored; // slow store: reads and writes yield, so unserialised handlers interleave
  const tick = () => new Promise((r) => setTimeout(r, 5));
  const slow = { get: async () => { await tick(); return stored && structuredClone(stored); },
                 put: async (x) => { await tick(); stored = structuredClone(x); } };
  const h = serialHandler();
  const options = [{ slot: "sat" }];
  await h(req("POST", { options, owners: ["ana", "ben"] }), "", slow);
  const dev = async (owner) => {
    const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const j = await (await h(req("POST", { owner, pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)) }), "/join", slow)).json();
    const v = verdictFor({ owner, hard: [], utility: [] }, options[0]);
    const sig = hex(await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey,
      verdictPayload({ option: options[0], owner, ...v, session: j.session, nonce: j.nonces[0] })));
    return { acceptable: v.acceptable, score: v.score, reason: v.reason, sig };
  };
  const [va, vb] = [await dev("ana"), await dev("ben")];
  const junk = [{ ...va, sig: "0".repeat(128) }];
  await Promise.all([
    h(req("POST", { owner: "ben", verdicts: [vb] }), "/verdicts", slow),
    h(req("POST", { owner: "ana", verdicts: junk }), "/verdicts", slow),
    h(req("POST", { owner: "ana", verdicts: junk }), "/verdicts", slow),
  ]);
  assert.ok(stored.verdicts.ben, "ben's accepted verdict survived the junk requests");
  assert.equal(stored.badStamps.ana.length, 2, "both bad attempts counted");
});
