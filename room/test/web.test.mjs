import { test } from "node:test";
import assert from "node:assert/strict";
import { handle } from "../relay/http.mjs";
import { HEIRS_OPTIONS, sheetFromAnswers, describeAnswers } from "../web/heirs.mjs";
import { newDevice, restoreDevice, createRoom, joinRoom, submitAnswers, getResult, getStatus, verifyResult } from "../web/client.mjs";

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
const answers = (over) => ({ favourite: null, never: [], maxMonths: null, maxMonthly: null, mustKeepHome: false,
                             noOneForcedOut: false, priorities: [], ...over });

async function runRoom(byOwner) {
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
  assert.deepEqual(await verifyResult(result, sents.marta), { ok: true });
  assert.deepEqual(await verifyResult(result, undefined), { ok: true });

  const rec = JSON.parse(result.transcript_json);
  // dishonest relay 1: announces a different decision
  assert.equal((await verifyResult({ ...result, decision: { id: "keep" } }, sents.marta)).why, "decision");
  // 2: edits the record (hash no longer matches)
  assert.equal((await verifyResult({ ...result, transcript_json: result.transcript_json.replace("buyout", "keep") }, sents.marta)).why, "hash");
  // 3: re-hashes an edited record: signature no longer covers it
  const forged = JSON.parse(JSON.stringify(rec));
  forged.entries[0].verdicts[0].score = 0.01;
  const { canonicalJson, Fl, sha256Hex } = await import("../engine.mjs");
  const json = canonicalJson({ ...forged, entries: forged.entries.map((e) => ({ ...e, verdicts: e.verdicts.map((v) => ({ ...v, score: new Fl(v.score) })) })) });
  assert.equal((await verifyResult({ ...result, transcript_json: json, transcript_hash: await sha256Hex(json) }, sents.marta)).why, "signature");
  // 4: swaps this person's key in the roster
  assert.equal((await verifyResult({ ...result, roster: { ...result.roster, marta: result.roster.javi } }, sents.marta)).why, "roster");
  // 5: record for another session
  assert.equal((await verifyResult({ ...result, session: "x".repeat(32) }, sents.marta)).why, "session");
  // 6: my own verdict is not what I sent
  const lie = { ...sents.marta, verdicts: sents.marta.verdicts.map((v, i) => i ? v : { ...v, score: v.score === 1 ? 0 : 1 }) };
  assert.equal((await verifyResult(result, lie)).why, "mine");
});

test("P1: the phone refuses a record with a verdict or an owner left out", async () => {
  const { result, sents } = await runRoom({
    marta: answers({ favourite: "buyout" }),
    javi: answers({ never: ["buyout"] }),     // javi red-lines buyout, so it can never be agreed
  });
  assert.equal(result.decision.id !== "buyout", true);
  const { canonicalJson, Fl, sha256Hex } = await import("../engine.mjs");
  const rebuild = async (mutate, roster = result.roster) => {
    const rec = JSON.parse(result.transcript_json);
    mutate(rec);
    const json = canonicalJson({ ...rec, entries: rec.entries.map((e) => ({ ...e, verdicts: e.verdicts.map((v) => ({ ...v, score: new Fl(v.score) })) })) });
    return { ...result, transcript_json: json, transcript_hash: await sha256Hex(json), roster };
  };
  // relay drops javi's red-line verdict on buyout, so buyout looks unanimous
  const dropOne = await rebuild((rec) => { const e = rec.entries.find((x) => x.option.id === "buyout"); e.verdicts = e.verdicts.filter((v) => v.owner !== "javi"); rec.result = { status: "agreed", decision: e.option }; });
  assert.equal((await verifyResult({ ...dropOne, status: "agreed", decision: dropOne.decision }, sents.marta)).ok, false);
  const incompleteNoSent = await verifyResult(dropOne, undefined);
  assert.equal(incompleteNoSent.why, "incomplete");
  // relay drops javi from every entry and from the roster: marta's phone knows who was in the room
  const dropOwner = await rebuild((rec) => { rec.entries.forEach((e) => { e.verdicts = e.verdicts.filter((v) => v.owner !== "javi"); }); },
    { marta: result.roster.marta });
  assert.equal((await verifyResult(dropOwner, sents.marta)).why, "owners");
  assert.equal(sents.marta.owners.length, 2);
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
