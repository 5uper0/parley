import { test } from "node:test";
import assert from "node:assert/strict";
import worker, { Room, Limiter, addressPrefix } from "../relay/worker.mjs";

const fakeStorage = () => { const m = new Map(); let alarm = null;
  return { m, get: async (k) => m.get(k), put: async (k, v) => { m.set(k, structuredClone(v)); },
           getAlarm: async () => alarm, setAlarm: async (t) => { alarm = t; }, deleteAll: async () => { m.clear(); alarm = null; } }; };

test("direct POST to a chosen room id never reaches the room object", async () => {
  let reached = false;
  const env = { LIMIT_SECRET: "s", ROOM: { idFromName: (n) => n, get: () => ({ fetch: async () => { reached = true; return new Response("{}", { status: 201 }); } }) },
                LIMIT: { idFromName: (n) => n, get: () => ({ fetch: async () => new Response("{}") }) } };
  const id = "a".repeat(32);
  const res = await worker.fetch(new Request(`https://r/rooms/${id}`, { method: "POST", body: "{}" }), env);
  assert.equal(res.status, 404);
  assert.equal(reached, false);
});

test("room creation is refused when the client is over the limit, and without a secret", async () => {
  const mk = (status, secret) => ({ LIMIT_SECRET: secret, ROOM: {}, LIMIT: { idFromName: (n) => n, get: () => ({ fetch: async () => new Response("{}", { status }) }) } });
  assert.equal((await worker.fetch(new Request("https://r/rooms", { method: "POST", body: "{}" }), mk(429, "s"))).status, 429);
  assert.equal((await worker.fetch(new Request("https://r/rooms", { method: "POST", body: "{}" }), mk(200, ""))).status, 500);
});

test("room sets one expiry alarm on first write and deletes everything when it fires", async () => {
  const st = fakeStorage();
  const room = new Room({ storage: st });
  const res = await room.fetch(new Request("https://r/rooms/x", { method: "POST", body: JSON.stringify({ options: [{ a: 1 }], owners: ["a", "b"] }) }));
  assert.equal(res.status, 201);
  const first = await st.getAlarm();
  assert.ok(first > Date.now());
  await room.alarm();
  assert.equal(st.m.size, 0);
  assert.equal(await st.getAlarm(), null);
});

test("limiter allows 20 an hour, then 429, and clears itself on alarm", async () => {
  const st = fakeStorage();
  const lim = new Limiter({ storage: st });
  for (let i = 0; i < 20; i++) assert.equal((await lim.fetch()).status, 200);
  assert.equal((await lim.fetch()).status, 429);
  assert.ok(await st.getAlarm());
  await lim.alarm();
  assert.equal(st.m.size, 0);
});

test("IPv6 clients share one limit per /64", () => {
  assert.equal(addressPrefix("1.2.3.4"), "1.2.3.4");
  assert.equal(addressPrefix("2001:db8:1:2:aaaa:bbbb:cccc:dddd"), addressPrefix("2001:db8:1:2::1"));
  assert.notEqual(addressPrefix("2001:db8:1:2::1"), addressPrefix("2001:db8:1:3::1"));
});

import { Records } from "../relay/worker.mjs";

function fakeStorage2() { const m = new Map(); let alarm = null;
  return { m, get: async (k) => m.get(k), put: async (k, v) => { m.set(k, structuredClone(v)); }, getAlarm: async () => alarm, setAlarm: async (t) => { alarm = t; }, deleteAll: async () => { m.clear(); alarm = null; }, alarmAt: () => alarm }; }

test("records entry: one object per token, written once, expires after 30 days, alarm wipes it", async () => {
  const st = fakeStorage2();
  const rec = new Records({ storage: st });
  const room = "b".repeat(32);
  assert.equal((await rec.fetch(new Request("https://r/", { method: "POST", body: JSON.stringify({ room: "bad" }) }))).status, 400);
  assert.equal((await rec.fetch(new Request("https://r/"))).status, 404);                       // empty object
  assert.equal((await rec.fetch(new Request("https://r/", { method: "POST", body: JSON.stringify({ room }) }))).status, 200);
  const first = st.m.get("e").at;
  assert.ok(st.alarmAt() > Date.now() + 29 * 86400000);                                           // wiped by an alarm
  assert.equal((await rec.fetch(new Request("https://r/", { method: "POST", body: JSON.stringify({ room: "c".repeat(32) }) }))).status, 200);
  assert.deepEqual(st.m.get("e"), { room, at: first });                                           // second register keeps the first entry
  assert.deepEqual(await (await rec.fetch(new Request("https://r/"))).json(), { room });
  assert.deepEqual(Object.keys(st.m.get("e")).sort(), ["at", "room"]);
  const real = Date.now; Date.now = () => real() + 31 * 86400000;
  try { assert.equal((await rec.fetch(new Request("https://r/"))).status, 404); } finally { Date.now = real; }
  await rec.alarm();
  assert.equal(st.m.size, 0);
});

function recEnv({ known = "a".repeat(32), roomStatus = 200 } = {}) {
  const calls = { room: 0, recordsNames: [], posts: [] };
  return { calls, LIMIT_SECRET: "s", COUNTERS: { idFromName: () => "c", get: () => ({ fetch: async () => new Response("{}") }) },
    RECORDS: { idFromName: (n) => (calls.recordsNames.push(n), n), get: (id) => ({ fetch: async (_u, init) => init?.method === "POST" ? (calls.posts.push({ id, ...JSON.parse(init.body) }), new Response("{}")) : id === known ? new Response(JSON.stringify({ room: "b".repeat(32) })) : new Response("{}", { status: 404 }) }) },
    ROOM: { idFromName: (n) => n, get: () => ({ fetch: async (u) => { calls.room++; const url = String(u);
      if (url.endsWith("/result")) return new Response(JSON.stringify({ record_token: "d".repeat(32) }));
      if (url.includes("/record?")) return new Response('{"status":"agreed"}', { status: roomStatus });
      return new Response('{"done":false}'); } }) } };
}

test("GET /records/<token>: unknown, malformed or vanished-room tokens all give the same 404 body; a known one is proxied without caching", async () => {
  const e = recEnv();
  const bodies = [];
  for (const t of ["z".repeat(32), "short", "c".repeat(32)]) { const r = await worker.fetch(new Request(`https://r/records/${t}`), e); assert.equal(r.status, 404); bodies.push(await r.text()); }
  assert.equal(e.calls.room, 0);
  const gone = recEnv({ roomStatus: 404 });
  const rg = await worker.fetch(new Request(`https://r/records/${"a".repeat(32)}`), gone);
  assert.equal(rg.status, 404);
  assert.equal(await rg.text(), bodies[0]);                                                       // same body as an unknown token
  const ok = await worker.fetch(new Request(`https://r/records/${"a".repeat(32)}`), e);
  assert.equal(ok.status, 200);
  assert.equal(ok.headers.get("cache-control"), "no-store");
});

test("record link is indexed when the room closes and on a result read, but not on an ordinary room request", async () => {
  const closed = "b".repeat(32);
  const run = async (method, path, body) => {
    const e = recEnv(); const pending = [];
    if (body === "done") e.ROOM = { idFromName: (n) => n, get: () => ({ fetch: async (u) => String(u).endsWith("/result") ? new Response(JSON.stringify({ record_token: "d".repeat(32) })) : new Response('{"done":true}') }) };
    await worker.fetch(new Request(`https://r/rooms/${closed}${path}`, { method, body: method === "POST" ? "{}" : undefined }), e, { waitUntil: (p) => pending.push(p) });
    await Promise.all(pending);
    return e.calls;
  };
  assert.deepEqual((await run("POST", "/verdicts", "done")).posts, [{ id: "d".repeat(32), room: closed }]);       // closed now
  assert.deepEqual((await run("GET", "/result")).posts, [{ id: "d".repeat(32), room: closed }]);                   // retry via result read
  assert.deepEqual((await run("POST", "/verdicts")).posts, []);                                                    // done:false: nothing
  assert.deepEqual((await run("POST", "/join")).posts, []);
});

test("a result read indexes the record link without a second room fetch", async () => {
  const closed = "b".repeat(32), posts = []; let roomCalls = 0;
  const env = { LIMIT_SECRET: "s", COUNTERS: { idFromName: () => "c", get: () => ({ fetch: async () => new Response("{}") }) },
    RECORDS: { idFromName: (n) => n, get: (id) => ({ fetch: async (_u, init) => (init?.method === "POST" && posts.push({ id, ...JSON.parse(init.body) }), new Response("{}")) }) },
    ROOM: { idFromName: (n) => n, get: () => ({ fetch: async () => (roomCalls++, new Response(JSON.stringify({ record_token: "e".repeat(32) }))) }) } };
  const pending = [];
  await worker.fetch(new Request(`https://r/rooms/${closed}/result`), env, { waitUntil: (p) => pending.push(p) });
  await Promise.all(pending);
  assert.equal(roomCalls, 1);                                                                    // only the read itself
  assert.deepEqual(posts, [{ id: "e".repeat(32), room: closed }]);
});
