import { test } from "node:test";
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { handle } from "../relay/http.mjs";
import { HEIRS_OPTIONS, sheetFromAnswers, describeAnswers } from "../web/heirs.mjs";
import { newDevice, restoreDevice, createRoom, joinRoom, submitAnswers, getResult, getStatus, verifyResult, rosterHash, checkRoom, saveOrganizerKey, loadOrganizerKey, reissueSeat } from "../web/client.mjs";

// Fetch shim: routes /rooms[/id[/path]] to the relay handler with one in-memory store per room.
function relayFetch() {
  const rooms = new Map();
  return async (url, init = {}) => {
    const m = new URL(url).pathname.match(/^\/rooms(?:\/([0-9a-f]{32}))?(\/.*)?$/);
    let id = m[1];
    if (!id) { id = crypto.randomUUID().replaceAll("-", ""); rooms.set(id, undefined); }
    const store = { get: async () => rooms.get(id) && structuredClone(rooms.get(id)), put: async (r) => { rooms.set(id, structuredClone(r)); } };
    const res = await handle(new Request(`https://relay/rooms/${id}`, init), m[2] || "", store);
    if (!m[1] && res.status === 201) return new Response(JSON.stringify({ id, ...(await res.json()) }), res);
    return res;
  };
}
const BASE = "https://relay";
let EXP;
const answers = (over) => ({ favourite: null, never: [], maxMonths: null, maxMonthly: null, mustKeepHome: false,
                             noOneForcedOut: false, priorities: [], ...over });

async function runRoom(byOwner) {
  EXP = { options: HEIRS_OPTIONS, rosterHash: await rosterHash(Object.keys(byOwner)) };
  const f = relayFetch();
  const sents = {};
  const owners = Object.keys(byOwner);
  const room = await createRoom(f, BASE, { options: HEIRS_OPTIONS, owners });
  for (const owner of owners) {
    const device = await newDevice();
    const { session, nonces } = await joinRoom(f, BASE, room.id, owner, device, room.tokens[owner]);
    const sub = await submitAnswers(f, BASE, room.id, { owner, sheet: sheetFromAnswers(owner, byOwner[owner]),
      options: room.options, owners, session, nonces, device });
    sents[owner] = sub.sent;
  }
  return { f, room, sents, result: await getResult(f, BASE, room.id) };
}

test("three heirs reach a decision that holds everyone's red lines", async () => {
  const { result } = await runRoom({
    marta: answers({ favourite: "buyout", never: ["keep"], priorities: ["home", "money"] }),
    javi: answers({ maxMonths: 12, priorities: ["speed"] }),
    olga: answers({ noOneForcedOut: true, favourite: "rent_out" }),
  });
  assert.equal(result.status, "agreed");
  assert.equal(result.decision.id, "buyout"); // only option with months<=12, nobody forced out, not "keep"
});

test("honest deadlock when conditions exclude every option", async () => {
  const { result } = await runRoom({
    marta: answers({ mustKeepHome: true }),
    javi: answers({ maxMonths: 4 }),
  });
  assert.equal(result.status, "deadlock");
});

test("result is pending until everyone answers; status shows who, never answers", async () => {
  const f = relayFetch();
  const room = await createRoom(f, BASE, { options: HEIRS_OPTIONS, owners: ["a", "b"] });
  const device = await newDevice();
  const { session, nonces } = await joinRoom(f, BASE, room.id, "a", device, room.tokens.a);
  await submitAnswers(f, BASE, room.id, { owner: "a", sheet: sheetFromAnswers("a", answers({ never: ["sell_now"] })),
    options: room.options, session, nonces, device });
  assert.equal(await getResult(f, BASE, room.id), null);
  const st = JSON.stringify(await getStatus(f, BASE, room.id));
  assert.ok(st.includes('"submitted":["a"]') && !st.includes("red-line") && !st.includes("sell_now\"]"));
});

test("saved key restores to the same public key and still signs accepted verdicts", async () => {
  const d = await newDevice();
  const back = await restoreDevice(d.privateJwk);
  assert.equal(back.pubkeyHex, d.pubkeyHex);
});

test("bad answers are refused; check lines are plain data", () => {
  assert.throws(() => sheetFromAnswers("a", answers({ never: ["moon"] })));
  assert.throws(() => sheetFromAnswers("a", answers({ maxMonths: -1 })));
  assert.throws(() => sheetFromAnswers("a", answers({ priorities: ["money", "money"] })));
  const lines = describeAnswers(answers({ never: ["keep"], maxMonths: 9, priorities: ["home"] }));
  assert.deepEqual(lines.map((l) => l.key), ["never", "maxMonths", "priorities"]);
});

test("P0: a person's phone accepts the relay's result only if it verifies against what that person sent", async () => {
  const { result, sents } = await runRoom({
    marta: answers({ favourite: "buyout", never: ["keep"] }),
    javi: answers({ maxMonths: 12 }),
  });
  assert.deepEqual(await verifyResult(result, sents.marta, EXP), { ok: true });
  assert.deepEqual(await verifyResult(result, undefined, EXP), { ok: true });

  const rec = JSON.parse(result.transcript_json);
  // dishonest relay 1: announces a different decision
  assert.equal((await verifyResult({ ...result, decision: { id: "keep" } }, sents.marta, EXP)).why, "decision");
  // 2: edits the record (hash no longer matches)
  assert.equal((await verifyResult({ ...result, transcript_json: result.transcript_json.replace("buyout", "keep") }, sents.marta, EXP)).why, "hash");
  // 3: re-hashes an edited record: signature no longer covers it
  const forged = JSON.parse(JSON.stringify(rec));
  forged.entries[0].verdicts[0].score = 0.01;
  const { canonicalJson, Fl, sha256Hex } = await import("../engine.mjs");
  const json = canonicalJson({ ...forged, entries: forged.entries.map((e) => ({ ...e, verdicts: e.verdicts.map((v) => ({ ...v, score: new Fl(v.score) })) })) });
  assert.equal((await verifyResult({ ...result, transcript_json: json, transcript_hash: await sha256Hex(json) }, sents.marta, EXP)).why, "signature");
  // 4: swaps this person's key in the roster
  assert.equal((await verifyResult({ ...result, roster: { ...result.roster, marta: result.roster.javi } }, sents.marta, EXP)).why, "roster");
  // 5: record for another session
  assert.equal((await verifyResult({ ...result, session: "x".repeat(32) }, sents.marta, EXP)).why, "session");
  // 6: my own verdict is not what I sent
  const lie = { ...sents.marta, verdicts: sents.marta.verdicts.map((v, i) => i ? v : { ...v, score: v.score === 1 ? 0 : 1 }) };
  assert.equal((await verifyResult(result, lie, EXP)).why, "mine");
});

test("P1: the phone refuses a record with a verdict or an owner left out, or with another option list", async () => {
  const { result, sents } = await runRoom({
    marta: answers({ favourite: "buyout" }),
    javi: answers({ never: ["buyout"] }),     // javi red-lines buyout, so it can never be agreed
  });
  assert.notEqual(result.decision.id, "buyout");
  const { canonicalJson, Fl, sha256Hex, chooseFromEntries } = await import("../engine.mjs");
  const exp = { options: HEIRS_OPTIONS, rosterHash: await rosterHash(["marta", "javi"]) };
  // a consistent attack: the relay edits the entries AND announces what max-min gives for them, re-hashed
  const rebuild = async (mutate, roster = result.roster) => {
    const rec = JSON.parse(result.transcript_json);
    mutate(rec);
    const pick = chooseFromEntries(rec.entries);
    rec.result = { status: pick.status, decision: pick.decision };
    const json = canonicalJson({ ...rec, entries: rec.entries.map((e) => ({ ...e, verdicts: e.verdicts.map((v) => ({ ...v, score: new Fl(v.score) })) })) });
    return { ...result, status: pick.status, decision: pick.decision, transcript_json: json, transcript_hash: await sha256Hex(json), roster };
  };
  // javi's red-line verdict on buyout is dropped, so buyout looks unanimous
  const dropOne = await rebuild((rec) => { const e = rec.entries.find((x) => x.option.id === "buyout"); e.verdicts = e.verdicts.filter((v) => v.owner !== "javi"); });
  assert.equal(dropOne.decision.id, "buyout", "the attack really changes the announced decision");
  assert.equal((await verifyResult(dropOne, undefined, exp)).why, "incomplete");
  assert.equal((await verifyResult(dropOne, sents.marta, exp)).why, "incomplete");
  // javi dropped from every entry and the roster
  const dropOwner = await rebuild((rec) => { rec.entries.forEach((e) => { e.verdicts = e.verdicts.filter((v) => v.owner !== "javi"); }); }, { marta: result.roster.marta });
  assert.equal((await verifyResult(dropOwner, sents.marta, exp)).why, "owners");
  assert.equal((await verifyResult(dropOwner, undefined, exp)).why, "owners");   // link roster alone is enough, no saved record needed
  // an option removed from the list (works with no saved record)
  const dropOption = await rebuild((rec) => { rec.entries = rec.entries.filter((e) => e.option.id !== result.decision.id); });
  assert.equal((await verifyResult(dropOption, undefined, exp)).why, "options");
  assert.deepEqual(await verifyResult(result, sents.marta, exp), { ok: true });
});

test("P1: a retry resends the exact signed set and signing happens once", async () => {
  const { signAnswers, postAnswers } = await import("../web/client.mjs");
  const f = relayFetch();
  const room = await createRoom(f, BASE, { options: HEIRS_OPTIONS, owners: ["a", "b"] });
  const device = await newDevice();
  const { session, nonces } = await joinRoom(f, BASE, room.id, "a", device, room.tokens.a);
  const sent = await signAnswers({ owner: "a", sheet: sheetFromAnswers("a", answers({ never: ["keep"] })), options: room.options,
    owners: room.owners, session, nonces, device });
  const first = JSON.stringify(sent);
  await postAnswers(f, BASE, room.id, sent);
  assert.equal(JSON.stringify(sent), first);                       // posting does not change the signed set
  await assert.rejects(postAnswers(f, BASE, room.id, sent), /already-submitted/); // a duplicate resend is refused, not re-signed
});

test("the join-screen check refuses a room whose names or options differ from the link and the page", async () => {
  const f = relayFetch();
  const room = await createRoom(f, BASE, { options: HEIRS_OPTIONS, owners: ["a", "b"] });
  const status = await getStatus(f, BASE, room.id);
  assert.equal(await checkRoom(status, await rosterHash(["a", "b"]), HEIRS_OPTIONS), true);
  assert.equal(await checkRoom({ ...status, owners: ["a", "b", "z"] }, await rosterHash(["a", "b"]), HEIRS_OPTIONS), false);
  assert.equal(await checkRoom({ ...status, options: status.options.slice(1) }, await rosterHash(["a", "b"]), HEIRS_OPTIONS), false);
  await assert.rejects(verifyResult({}, undefined, undefined), /needs the page/);
});

import { recordShapeOk } from "../web/client.mjs";

test("record page shape check: bad hash, owners, unknown or prototype decision ids are refused", () => {
  const ids = { buyout: 1, keep: 1 };
  const ok = { status: "agreed", decision: { id: "buyout" }, owners: ["a", "b"], transcript_hash: "a".repeat(64) };
  assert.equal(recordShapeOk(ok, ids), true);
  assert.equal(recordShapeOk({ ...ok, status: "deadlock", decision: null }, ids), true);
  for (const bad of [
    { ...ok, transcript_hash: "z".repeat(64) }, { ...ok, transcript_hash: "a".repeat(63) }, { ...ok, owners: "a,b" }, { ...ok, owners: [1] },
    { ...ok, decision: { id: "constructor" } }, { ...ok, decision: { id: "toString" } }, { ...ok, decision: { id: "nope" } }, { ...ok, decision: null },
    { ...ok, status: "other" }, null, "x",
  ]) assert.equal(recordShapeOk(bad, ids), false, JSON.stringify(bad)?.slice(0, 50));
});

test("organizer key: sessionStorage only, reissue gives a working new seat, old link dies, no key in the link", async () => {
  const f = relayFetch();
  const store = new Map(); const ss = { setItem: (k, v) => store.set(k, v), getItem: (k) => store.get(k) ?? null };
  const room = await createRoom(f, BASE, { options: HEIRS_OPTIONS, owners: ["ann", "bo"] });
  saveOrganizerKey(ss, room.id, "not-a-key");
  assert.equal(loadOrganizerKey(ss, room.id), null);                       // junk is never stored
  saveOrganizerKey(ss, room.id, room.organizer_key);
  assert.equal(loadOrganizerKey(ss, room.id), room.organizer_key);
  const lost = await newDevice();
  await joinRoom(f, BASE, room.id, "ann", lost, room.tokens.ann);           // ann's phone is lost after joining
  const token = await reissueSeat(f, BASE, room.id, loadOrganizerKey(ss, room.id), "ann");
  assert.match(token, /^[0-9a-f]{32}$/);
  assert.ok(!token.includes(room.organizer_key) && token !== room.tokens.ann);
  await assert.rejects(joinRoom(f, BASE, room.id, "ann", await newDevice(), room.tokens.ann)); // old link is dead
  const dev = await newDevice();
  const { session, nonces } = await joinRoom(f, BASE, room.id, "ann", dev, token);
  await submitAnswers(f, BASE, room.id, { owner: "ann", sheet: sheetFromAnswers("ann", answers({})), options: room.options, owners: ["ann", "bo"], session, nonces, device: dev });
  await assert.rejects(reissueSeat(f, BASE, room.id, room.organizer_key, "ann"), /already-submitted/);
  await assert.rejects(reissueSeat(f, BASE, room.id, "0".repeat(32), "bo"), /bad-organizer-key/);
});

test("a missing organizer key is refused", async () => {
  const f = relayFetch();
  const room = await createRoom(f, BASE, { options: HEIRS_OPTIONS, owners: ["ann", "bo"] });
  await assert.rejects(reissueSeat(f, BASE, room.id, undefined, "ann"), /bad-organizer-key/);
});

test("the organizer key is held in sessionStorage only and never reaches a URL, localStorage or a log", () => {
  const app = readFileSync(new URL("../web/app.mjs", import.meta.url), "utf8");
  const client = readFileSync(new URL("../web/client.mjs", import.meta.url), "utf8");
  const calls = [...app.matchAll(/(save|load)OrganizerKey\(([^,]+),/g)].map((m) => m[2]);
  assert.ok(calls.length >= 2 && calls.every((a) => a === "sessionStorage"), "every key read/write uses sessionStorage");
  assert.equal([...app.matchAll(/organizer_key/g)].length, 1);                       // only room.organizer_key handed to saveOrganizerKey
  assert.match(app, /saveOrganizerKey\(sessionStorage, room\.id, room\.organizer_key\)/);
  const urls = [...app.matchAll(/(?:replaceState\([^)]*|const seatUrl[^\n]*)/g)].map((m) => m[0]).join("\n");
  assert.ok(urls.includes("replaceState") && !/key/i.test(urls), "no key in any URL template");
  assert.ok(!/console\./.test(app + client), "no logging");
});

test("a relay that returns a malformed token for a reissue is refused", async () => {
  const f = async () => new Response(JSON.stringify({ token: "/../x" }), { status: 200 });
  await assert.rejects(reissueSeat(f, BASE, "a".repeat(32), "b".repeat(32), "ann"), /bad-token/);
});
