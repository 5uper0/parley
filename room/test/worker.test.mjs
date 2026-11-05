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
