import { readFileSync } from "node:fs";
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
    r = await handle(req("POST", { owner, pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)), token: pub.tokens[owner] }), "/join", s);
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
  const made = await (await handle(req("POST", { options, owners: ["ana", "ben"] }), "", s)).json();
  const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  await handle(req("POST", { owner: "ana", pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)), token: made.tokens.ana }), "/join", s);
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
  const made = await (await h(req("POST", { options, owners: ["ana", "ben"] }), "", slow)).json();
  const dev = async (owner) => {
    const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const j = await (await h(req("POST", { owner, pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)), token: made.tokens[owner] }), "/join", slow)).json();
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

test("P0: knowing a name is not enough: join needs the person's token; tokens are not in the public view", async () => {
  const s = mkStore();
  const made = await (await handle(req("POST", { options: [{ a: 1 }], owners: ["ann", "bob"] }), "", s)).json();
  const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  const pubkey_hex = hex(await crypto.subtle.exportKey("raw", kp.publicKey));
  const wrong = await handle(req("POST", { owner: "bob", pubkey_hex, token: made.tokens.ann }), "/join", s); // ann's token, bob's seat
  assert.equal(wrong.status, 400);
  assert.deepEqual(await wrong.json(), { error: "bad-token" });
  assert.equal((await handle(req("POST", { owner: "bob", pubkey_hex }), "/join", s)).status, 400);
  const view = JSON.stringify(await (await handle(req("GET"), "", s)).json());
  assert.ok(!view.includes(made.tokens.ann) && !view.includes(made.tokens.bob) && !view.includes("tokens"));
  assert.equal((await handle(req("POST", { owner: "bob", pubkey_hex, token: made.tokens.bob }), "/join", s)).status, 200);
});

test("seat identity: a link preview GET binds nothing, a second device is refused, the creator can reissue a lost seat", async () => {
  const s = mkStore();
  const made = await (await handle(req("POST", { options: [{ a: 1 }], owners: ["ann", "bob"] }), "", s)).json();
  assert.match(made.organizer_key, /^[0-9a-f]{32}$/);
  // preview bots GET the page data: nobody is bound
  for (const path of ["", "/result"]) await handle(req("GET"), path, s);
  assert.deepEqual((await (await handle(req("GET"), "", s)).json()).joined, []);
  const key = async () => hex(await crypto.subtle.exportKey("raw", (await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"])).publicKey));
  const join = async (owner, token) => handle(req("POST", { owner, pubkey_hex: await key(), token }), "/join", s);
  assert.equal((await join("ann", made.tokens.ann)).status, 200);
  assert.equal((await (await join("ann", made.tokens.ann)).json()).error, "already-joined");   // second device, same token
  // reissue needs the creator's key; wrong guesses are counted and then locked out
  const reissue = (organizer_key, owner) => handle(req("POST", { organizer_key, owner }), "/reissue", s);
  for (let i = 0; i < 5; i++) assert.equal((await (await reissue("0".repeat(32), "ann")).json()).error, "bad-organizer-key");
  assert.equal((await (await reissue("1".repeat(32), "ann")).json()).error, "locked");        // more guessing is locked
  assert.equal((await reissue(made.organizer_key, "ann")).status, 200);                         // the creator is never locked out
});

test("reissue with the right key: new token, old token dead, fresh nonces, a working new seat", async () => {
  const s = mkStore();
  const options = [{ a: 1 }, { a: 2 }];
  const made = await (await handle(req("POST", { options, owners: ["ann", "bob"] }), "", s)).json();
  const pub = async () => hex(await crypto.subtle.exportKey("raw", (await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"])).publicKey));
  const join = async (owner, token) => handle(req("POST", { owner, pubkey_hex: await pub(), token }), "/join", s);
  const first = await (await join("ann", made.tokens.ann)).json();
  const { token } = await (await handle(req("POST", { organizer_key: made.organizer_key, owner: "ann" }), "/reissue", s)).json();
  assert.notEqual(token, made.tokens.ann);
  assert.equal((await (await join("ann", made.tokens.ann)).json()).error, "bad-token");       // old link is dead
  const secondRes = await join("ann", token);
  assert.equal(secondRes.status, 200);                                                           // the seat really was freed
  const second = await secondRes.json();
  assert.equal(second.nonces.length, options.length);
  assert.notDeepEqual(second.nonces, first.nonces);                                              // nothing signed earlier replays
  const view = JSON.stringify(await (await handle(req("GET"), "", s)).json());
  assert.ok(!view.includes(made.organizer_key) && !view.includes("organizer"));                 // never in the public view
});

test("reissue guards: unknown owner, submitted seat is final, closed room, bad stamps cleared", async () => {
  const s = mkStore();
  const options = [{ a: 1 }];
  const made = await (await handle(req("POST", { options, owners: ["ann", "bob"] }), "", s)).json();
  const re = (owner, key = made.organizer_key) => handle(req("POST", { organizer_key: key, owner }), "/reissue", s);
  assert.equal((await (await re("zed")).json()).error, "unknown-owner");                        // right key, unknown owner
  const dev = async (owner) => {
    const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const j = await (await handle(req("POST", { owner, pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)), token: made.tokens[owner] }), "/join", s)).json();
    const v = verdictFor({ owner, hard: [], utility: [] }, options[0]);
    const sig = hex(await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey, verdictPayload({ option: options[0], owner, ...v, session: j.session, nonce: j.nonces[0] })));
    return [{ acceptable: v.acceptable, score: v.score, reason: v.reason, sig }];
  };
  const annV = await dev("ann");
  // junk from ann's lost device locks her, reissue clears it for the new device
  for (let i = 0; i < 5; i++) await handle(req("POST", { owner: "ann", verdicts: [{ ...annV[0], sig: "0".repeat(128) }] }), "/verdicts", s);
  assert.equal((await handle(req("POST", { owner: "ann", verdicts: annV }), "/verdicts", s)).status, 429);
  assert.equal((await re("ann")).status, 200);
  assert.equal((await handle(req("GET"), "", s)).status, 200);
  const stored = await s.get();
  assert.equal(stored.badStamps.ann, undefined);
  // a submitted seat is final
  await handle(req("POST", { owner: "bob", pubkey_hex: hex(await crypto.subtle.exportKey("raw", (await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"])).publicKey)), token: made.tokens.bob }), "/join", s);
  const bobStored = await s.get();
  assert.ok(bobStored.roster.bob);
  // close the room by hand-marking a result, then reissue is refused
  const closed = await s.get(); closed.result = { status: "agreed" }; await s.put(closed);
  assert.equal((await (await re("bob")).json()).error, "room-closed");
});

test("a submitted seat cannot be reissued", async () => {
  const s = mkStore();
  const options = [{ a: 1 }];
  const made = await (await handle(req("POST", { options, owners: ["ann", "bob"] }), "", s)).json();
  const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  const j = await (await handle(req("POST", { owner: "ann", pubkey_hex: hex(await crypto.subtle.exportKey("raw", kp.publicKey)), token: made.tokens.ann }), "/join", s)).json();
  const v = verdictFor({ owner: "ann", hard: [], utility: [] }, options[0]);
  const sig = hex(await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey, verdictPayload({ option: options[0], owner: "ann", ...v, session: j.session, nonce: j.nonces[0] })));
  assert.equal((await handle(req("POST", { owner: "ann", verdicts: [{ acceptable: v.acceptable, score: v.score, reason: v.reason, sig }] }), "/verdicts", s)).status, 200);
  assert.equal((await (await handle(req("POST", { organizer_key: made.organizer_key, owner: "ann" }), "/reissue", s)).json()).error, "already-submitted");
});

test("the relay writes no logs (tokens and keys never reach a log line)", () => {
  for (const f of ["core.mjs", "http.mjs", "worker.mjs"]) {
    assert.ok(!/console\./.test(readFileSync(new URL(`../relay/${f}`, import.meta.url), "utf8")), `${f} logs`);
  }
});
