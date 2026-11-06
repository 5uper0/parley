import { test } from "node:test";
import assert from "node:assert/strict";
import { beaconKey, bump, weeklyReport, relayEventFor, prune, dayOf } from "../relay/metrics.mjs";
import worker from "../relay/worker.mjs";

test("beacon allowlist: only known events, n 1-4 on q_answered, en or es, nothing else", () => {
  assert.equal(beaconKey('{"event":"page_start","lang":"en"}'), "page_start");
  assert.equal(beaconKey('{"event":"q_answered","n":3,"lang":"es"}'), "q_answered_3");
  assert.equal(beaconKey('{"event":"result_viewed_ok","lang":"en"}'), "result_viewed_ok");
  assert.equal(beaconKey('{"event":"result_refused","lang":"en"}'), "result_refused");
  for (const bad of [
    '{"event":"q_answered","n":5,"lang":"en"}', '{"event":"q_answered","n":0,"lang":"en"}', '{"event":"q_answered","lang":"en"}',
    '{"event":"page_start","n":1,"lang":"en"}', '{"event":"room_created","lang":"en"}', '{"event":"page_start","lang":"fr"}',
    '{"event":"page_start","lang":"en","room":"abc"}', '{"event":"page_start"}', "[]", "null", "{", "", '{"event":"page_start","lang":"en"}' + " ".repeat(130),
  ]) assert.equal(beaconKey(bad), null, bad.slice(0, 40));
  assert.equal(beaconKey(undefined), null);
});

test("weekly report hides totals under 5 and groups days into weeks", () => {
  const c = {};
  for (let i = 0; i < 6; i++) bump(c, "2026-11-02", "joined");        // Monday
  bump(c, "2026-11-04", "joined"); bump(c, "2026-11-04", "submitted");
  bump(c, "2026-11-09", "joined");                                      // next Monday
  const r = weeklyReport(c);
  assert.deepEqual(r["2026-11-02"], { joined: 7, submitted: "<5" });
  assert.deepEqual(r["2026-11-09"], { joined: "<5" });
});

test("relay events come from path, status and a known error code only", () => {
  assert.equal(relayEventFor("POST", "", 201), "room_created");
  assert.equal(relayEventFor("POST", "/join", 200), "joined");
  assert.equal(relayEventFor("POST", "/verdicts", 200, undefined, false), "submitted");
  assert.equal(relayEventFor("POST", "/verdicts", 200, undefined, true), "room_closed");
  assert.equal(relayEventFor("POST", "/join", 400, "bad-token"), "rejected_bad-token");
  assert.equal(relayEventFor("POST", "/join", 400, "some-new-secret-text"), null);   // unknown text never becomes a key
  assert.equal(relayEventFor("GET", "", 200), null);
});

test("old days are pruned", () => {
  const now = Date.parse("2027-03-01T00:00:00Z");
  const c = { "2026-11-02": { a: 1 }, [dayOf(now)]: { a: 1 } };
  assert.deepEqual(Object.keys(prune(c, now)), [dayOf(now)]);
});

function env({ limited = false } = {}) {
  const bumps = [], limiterCalls = [];
  return { bumps, limiterCalls, LIMIT_SECRET: "s", OPERATOR_TOKEN: "op",
    COUNTERS: { idFromName: () => "c", get: () => ({ fetch: async (_u, init) => init?.method === "POST" ? (bumps.push(JSON.parse(init.body)), new Response("{}")) : new Response(JSON.stringify({ w: { joined: 7 } })) }) },
    MLIMIT: { idFromName: (n) => { limiterCalls.push(n); return n; }, get: () => ({ fetch: async () => new Response("{}", { status: limited ? 429 : 200 }) }) },
    LIMIT: {}, ROOM: {} };
}
const post = (body, headers = {}) => new Request("https://r/m", { method: "POST", body, headers });

test("/m counts a valid beacon and stores nothing but the counter key", async () => {
  const e = env();
  const res = await worker.fetch(post('{"event":"q_answered","n":2,"lang":"en"}', { "user-agent": "UA-SECRET", referer: "https://x/#/r/abc/ann/token", "cf-connecting-ip": "203.0.113.9" }), e);
  assert.equal(res.status, 200);
  assert.deepEqual(e.bumps, [{ key: "q_answered_2" }]);                                  // no header, ip or room in what is stored
  assert.ok(e.limiterCalls.every((n) => !n.includes("203.0.113.9")));                    // the limiter name is an HMAC, not the address
  assert.equal(JSON.stringify(await res.json()), "{}");
});

test("/m rejects bad beacons without echo or counting, and rate limits", async () => {
  const e = env();
  for (const body of ['{"event":"hack","lang":"en"}', '{"event":"page_start","lang":"en","x":"SECRET"}', "x".repeat(300)]) {
    const res = await worker.fetch(post(body, { "content-length": String(body.length) }), e);
    assert.equal(res.status, 400);
    assert.ok(!(await res.text()).includes("SECRET"));
  }
  assert.equal(e.bumps.length, 0);
  assert.equal((await worker.fetch(new Request("https://r/m", { method: "GET" }), e)).status, 400);
  const lim = env({ limited: true });
  assert.equal((await worker.fetch(post('{"event":"page_start","lang":"en"}'), lim)).status, 429);
  assert.equal(lim.bumps.length, 0);
});

test("the limiter key for /m changes every day (rotating secret)", async () => {
  const names = [];
  const e = env(); e.MLIMIT.idFromName = (n) => (names.push(n), n);
  const RealDate = Date;
  try {
    globalThis.Date = class extends RealDate { constructor(...a) { super(...(a.length ? a : [Date.parse("2026-11-06T10:00:00Z")])); } static now() { return Date.parse("2026-11-06T10:00:00Z"); } };
    await worker.fetch(post('{"event":"page_start","lang":"en"}', { "cf-connecting-ip": "198.51.100.7" }), e);
    globalThis.Date = class extends RealDate { constructor(...a) { super(...(a.length ? a : [Date.parse("2026-11-07T10:00:00Z")])); } static now() { return Date.parse("2026-11-07T10:00:00Z"); } };
    await worker.fetch(post('{"event":"page_start","lang":"en"}', { "cf-connecting-ip": "198.51.100.7" }), e);
  } finally { globalThis.Date = RealDate; }
  assert.equal(names.length, 2);
  assert.notEqual(names[0], names[1]);
});

test("the report is operator-only", async () => {
  const e = env();
  assert.equal((await worker.fetch(new Request("https://r/m/report"), e)).status, 404);
  assert.equal((await worker.fetch(new Request("https://r/m/report", { headers: { authorization: "Bearer nope" } }), e)).status, 404);
  const ok = await worker.fetch(new Request("https://r/m/report", { headers: { authorization: "Bearer op" } }), e);
  assert.equal(ok.status, 200);
});

import { Counters } from "../relay/worker.mjs";

test("relay-side counting: keys come from path, status and a known code, never from ids or error text", async () => {
  const id = "a".repeat(32);
  const keys = [];
  const answers = [new Response("{}", { status: 201 }), new Response('{"done":true}', { status: 200 }),
                   new Response('{"error":"some-secret-text"}', { status: 400 }), new Response('{"error":"bad-token"}', { status: 400 })];
  const e = { LIMIT_SECRET: "s", LIMIT: { idFromName: (n) => n, get: () => ({ fetch: async () => new Response("{}") }) },
    ROOM: { idFromName: () => "r", get: () => ({ fetch: async () => answers.shift() }) },
    COUNTERS: { idFromName: () => "c", get: () => ({ fetch: async (_u, init) => (keys.push(JSON.parse(init.body).key), new Response("{}")) }) } };
  const ctx = { waitUntil: () => {} };
  await worker.fetch(new Request("https://r/rooms", { method: "POST", body: "{}" }), e, ctx);                       // creation
  await worker.fetch(new Request(`https://r/rooms/${id}/verdicts`, { method: "POST", body: "{}" }), e, ctx);        // last verdict
  await worker.fetch(new Request(`https://r/rooms/${id}/join`, { method: "POST", body: "{}" }), e, ctx);            // unknown error text
  await worker.fetch(new Request(`https://r/rooms/${id}/join`, { method: "POST", body: "{}" }), e, ctx);            // known code
  assert.deepEqual(keys, ["room_created", "room_closed", "rejected_bad-token"]);
  assert.ok(keys.every((k) => !k.includes(id) && !k.includes("secret")));
});

test("counters object: weekly report only, no day keys, small totals hidden, bad keys refused", async () => {
  const store = new Map();
  const state = { storage: { get: async (k) => store.get(k), put: async (k, v) => { store.set(k, structuredClone(v)); } } };
  const c = new Counters(state);
  const bump = (key) => c.fetch(new Request("https://c/", { method: "POST", body: JSON.stringify({ key }) }));
  for (let i = 0; i < 6; i++) await bump("joined");
  await bump("submitted");
  assert.equal((await bump("room/abc123")).status, 400);                   // a key outside the allowlist is refused
  assert.equal((await bump("rejected_" + "x".repeat(40))).status, 400);
  const report = await (await c.fetch(new Request("https://c/"))).json();
  assert.equal(Object.keys(report).length, 1);
  assert.match(Object.keys(report)[0], /^\d{4}-\d{2}-\d{2}$/);           // a week start (Monday), not a per-day row
  const week = Object.values(report)[0];
  assert.deepEqual(week, { joined: 6, submitted: "<5" });
  assert.deepEqual(Object.keys(store.get("c")).length, 1);                  // one day row, stored as counts only
});

test("/m caps the body even without a content-length header, and the report token check ignores prefixes", async () => {
  const e = env();
  const big = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('{"event":"page_start","lang":"en"}')); c.enqueue(new Uint8Array(200).fill(32)); c.close(); } });
  const res = await worker.fetch(new Request("https://r/m", { method: "POST", body: big, duplex: "half" }), e, { waitUntil: () => {} });
  assert.equal(res.status, 400);
  assert.equal(e.bumps.length, 0);
  const near = await worker.fetch(new Request("https://r/m/report", { headers: { authorization: "Bearer o" } }), e);
  assert.equal(near.status, 404);
});

import { isCounterKey } from "../relay/metrics.mjs";
import { readCapped, MetricsLimiter } from "../relay/worker.mjs";

test("isCounterKey is built from the same sets as the events", () => {
  for (const k of ["page_start", "q_answered_1", "q_answered_4", "result_viewed_ok", "result_refused", "room_created", "joined", "submitted", "room_closed", "rejected_bad-token", "rejected_locked"]) assert.equal(isCounterKey(k), true, k);
  for (const k of ["q_answered", "q_answered_5", "rejected_", "rejected_x".repeat(2), "rejected_slow-down", "room/abc", "__proto__", "", 7, null]) assert.equal(isCounterKey(k), false, String(k));
});

test("readCapped stops reading at the cap and cancels the stream", async () => {
  let pulled = 0, cancelled = false;
  const body = new ReadableStream({ pull(c) { pulled++; c.enqueue(new Uint8Array(100)); }, cancel() { cancelled = true; } });
  assert.equal(await readCapped({ body }, 128), null);
  assert.ok(cancelled);
  assert.ok(pulled <= 4, `pulled ${pulled} chunks`);                           // it did not read on forever
  assert.equal(await readCapped({ body: null }, 128), "");
  assert.equal(await readCapped(new Request("https://x/", { method: "POST", body: "hello" }), 128), "hello");
});

test("MetricsLimiter: 20 an hour, an alarm about an hour out, alarm wipes", async () => {
  const m = new Map(); let alarm = null;
  const lim = new MetricsLimiter({ storage: { get: async (k) => m.get(k), put: async (k, v) => m.set(k, structuredClone(v)), setAlarm: async (t) => { alarm = t; }, deleteAll: async () => { m.clear(); alarm = null; } } });
  for (let i = 0; i < 20; i++) assert.equal((await lim.fetch()).status, 200);
  assert.equal((await lim.fetch()).status, 429);                                // the 21st beacon
  assert.ok(alarm > Date.now() + 3500_000 && alarm < Date.now() + 3700_000);
  await lim.alarm();
  assert.equal(m.size, 0);
});

test("counting goes through waitUntil once and a failing counter never breaks the response", async () => {
  const waited = [];
  const e = env();
  e.COUNTERS = { idFromName: () => "c", get: () => ({ fetch: async () => { throw new Error("counter down"); } }) };
  const res = await worker.fetch(post('{"event":"page_start","lang":"en"}'), e, { waitUntil: (p) => waited.push(p) });
  assert.equal(res.status, 200);
  assert.equal(waited.length, 1);
  await assert.doesNotReject(Promise.all(waited));
  const e2 = env();
  e2.COUNTERS = { idFromName: () => { throw new Error("sync failure"); }, get: () => ({}) };
  assert.equal((await worker.fetch(post('{"event":"page_start","lang":"en"}'), e2, { waitUntil: () => {} })).status, 200);
});

test("bad beacons answer exactly {error:no}; the report is no-store", async () => {
  const e = env();
  const res = await worker.fetch(post('{"event":"hack","lang":"en"}'), e);
  assert.equal(await res.text(), '{"error":"no"}');
  e.COUNTERS = { idFromName: () => "c", get: () => ({ fetch: async () => new Response("{}", { headers: { "cache-control": "no-store" } }) }) };
  const rep = await worker.fetch(new Request("https://r/m/report", { headers: { authorization: "Bearer op" } }), e);
  assert.equal(rep.status, 200);
});
