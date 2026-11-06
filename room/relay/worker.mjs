// Cloudflare Worker entry. One Durable Object per room; its id is the secret room link.
// The relay holds an option list, public keys and signed masked verdicts. Never sheets.

import { serialHandler } from "./http.mjs";
import { rateAllow, ROOM_TTL_MS } from "./core.mjs";
import { MAX_BODY_BYTES, isCounterKey, beaconKey, bump, prune, dayOf, weeklyReport, relayEventFor } from "./metrics.mjs";

const ROOMS_PER_HOUR = 20, BEACONS_PER_HOUR = 20;

export class Room {
  constructor(state) { this.state = state; this.handle = serialHandler(); }
  async alarm() { await this.state.storage.deleteAll(); } // room expired: nothing is kept

  fetch(request) {
    const url = new URL(request.url);
    const store = {
      get: () => this.state.storage.get("room"),
      put: async (room) => {
        await this.state.storage.put("room", room);
        if (!(await this.state.storage.getAlarm())) await this.state.storage.setAlarm(Date.now() + ROOM_TTL_MS);
      },
    };
    return this.handle(request, url.pathname.replace(/^\/rooms\/[^/]+/, ""), store);
  }
}

/** One counter per client. The key is an HMAC of the address (IPv6 cut to its /64) under a secret, so the
 *  object name cannot be turned back into an address without the secret; stamps expire one window later. */
export class Limiter {
  constructor(state) { this.state = state; }
  async alarm() { await this.state.storage.deleteAll(); }
  async fetch() {
    const next = rateAllow((await this.state.storage.get("t")) || [], Date.now(), ROOMS_PER_HOUR, 3600_000);
    if (!next) return new Response("{}", { status: 429 });
    await this.state.storage.put("t", next);
    await this.state.storage.setAlarm(Date.now() + 3600_000 + 60_000);
    return new Response("{}");
  }
}

/** Beacon rate limit: one object per client, named by a key that rotates daily, wiped one hour after the last use. */
export class MetricsLimiter {
  constructor(state) { this.state = state; }
  async alarm() { await this.state.storage.deleteAll(); }
  async fetch() {
    const next = rateAllow((await this.state.storage.get("t")) || [], Date.now(), BEACONS_PER_HOUR, 3600_000);
    if (!next) return new Response("{}", { status: 429 });
    await this.state.storage.put("t", next);
    await this.state.storage.setAlarm(Date.now() + 3600_000);
    return new Response("{}");
  }
}

/** One object per record token: {room, at}, written once, wiped by an alarm 30 days later. Holds no names, answers or keys. */
export class Records {
  constructor(state) { this.state = state; }
  async alarm() { await this.state.storage.deleteAll(); }
  async fetch(request) {
    const now = Date.now();
    if (request.method === "GET") {
      const e = await this.state.storage.get("e");
      return e && now - e.at < ROOM_TTL_MS ? new Response(JSON.stringify({ room: e.room }), { status: 200 }) : new Response("{}", { status: 404 });
    }
    const { room } = await request.json();                // parsed first: nothing is awaited between the check and the write below
    if (!/^[0-9a-f]{32}$/.test(room)) return new Response("{}", { status: 400 });
    if (await this.state.storage.get("e")) return new Response("{}");   // already registered: keep the first entry and its date
    await this.state.storage.put("e", { room, at: now });
    await this.state.storage.setAlarm(now + ROOM_TTL_MS);
    return new Response("{}");
  }
}

/** The only place counters live: day -> key -> number. POST /bump {key} adds one; GET returns the weekly report. */
export class Counters {
  constructor(state) { this.state = state; }
  async fetch(request) {
    if (request.method === "GET") {
      const counters = (await this.state.storage.get("c")) || {};
      return new Response(JSON.stringify(weeklyReport(counters)), { headers: { "content-type": "application/json", "cache-control": "no-store" } });
    }
    const { key } = await request.json();               // parse first: nothing is awaited between the read and the write below
    if (!isCounterKey(key)) return new Response("{}", { status: 400 });
    const counters = (await this.state.storage.get("c")) || {};
    await this.state.storage.put("c", prune(bump(counters, dayOf(Date.now()), key), Date.now()));
    return new Response("{}");
  }
}

export function addressPrefix(ip) {
  if (!ip.includes(":")) return ip;
  const full = ip.includes("::") ? ip.replace("::", ":" + "0:".repeat(Math.max(0, 8 - ip.split(":").filter(Boolean).length)) ) : ip;
  return full.split(":").slice(0, 4).join(":");
}

async function clientKey(request, secret) {
  const ip = addressPrefix(request.headers.get("cf-connecting-ip") || "unknown");
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(ip));
  return Array.from(new Uint8Array(mac).slice(0, 16), (b) => b.toString(16).padStart(2, "0")).join("");
}

// Counting never delays a response: it runs after it (ctx.waitUntil) and its failure is ignored.
const count = (env, ctx, key) => {
  if (!env.COUNTERS || !key) return;
  try {
    const p = env.COUNTERS.get(env.COUNTERS.idFromName("all")).fetch("https://c/", { method: "POST", body: JSON.stringify({ key }) }).catch(() => {});
    if (ctx?.waitUntil) ctx.waitUntil(p);
    return p;
  } catch { /* a failed count never fails a room request */ }
};

/** Run a room request and count what happened from path, status and error code only. */
async function counted(env, ctx, request, path, run, roomId) {
  const res = await run();
  let code, done, token;
  if (res.status >= 400 || (request.method === "POST" && path === "/verdicts")) {
    try { const b = await res.clone().json(); code = b.error; done = b.done; } catch { /* not json */ }
  } else if (request.method === "GET" && path === "/result" && res.status === 200) {
    try { token = (await res.clone().json()).record_token; } catch { /* not json */ }   // already in the response: no second room fetch
  }
  count(env, ctx, relayEventFor(request.method, path, res.status, code, done));
  // The room just closed, or a client reads a closed room's result: (re)index its record link. Idempotent, so retries are free.
  if (roomId && env.RECORDS && (done === true || (request.method === "GET" && path === "/result" && res.status === 200))) {
    const p = registerRecord(env, roomId, token).catch(() => {});
    if (ctx?.waitUntil) ctx.waitUntil(p);
  }
  return res;
}

/** Reads at most `max` bytes of the body, whatever the headers claim; null if it is longer. */
export async function readCapped(request, max) {
  if (!request.body) return "";
  const reader = request.body.getReader(), parts = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.length;
    if (total > max) { await reader.cancel(); return null; }
    parts.push(value);
  }
  return new TextDecoder().decode(Uint8Array.from(parts.flatMap((p) => [...p])));
}

async function sameToken(given, expected) {
  const enc = (x) => new TextEncoder().encode(String(x));
  const [a, b] = await Promise.all([crypto.subtle.digest("SHA-256", enc(given)), crypto.subtle.digest("SHA-256", enc(expected))]);
  const x = new Uint8Array(a), y = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];     // hashes first: fixed length, no early exit on the secret
  return diff === 0;
}

async function registerRecord(env, roomId, known) {
  let record_token = known;
  if (!record_token) {                                   // the room just closed: read the token from the room
    const r = await env.ROOM.get(env.ROOM.idFromName(roomId)).fetch(`https://r/rooms/${roomId}/result`);
    ({ record_token } = await r.json());
  }
  if (!/^[0-9a-f]{32}$/.test(record_token || "")) return;
  await env.RECORDS.get(env.RECORDS.idFromName(record_token)).fetch("https://r/", { method: "POST", body: JSON.stringify({ room: roomId }) });
}

async function handleRecord(env, token) {
  const nf = () => new Response(JSON.stringify({ error: "not-found" }), { status: 404 });
  if (!env.RECORDS || !/^[0-9a-f]{32}$/.test(token)) return nf();
  const hit = await env.RECORDS.get(env.RECORDS.idFromName(token)).fetch("https://r/");
  if (hit.status !== 200) return nf();
  const { room } = await hit.json();
  const res = await env.ROOM.get(env.ROOM.idFromName(room)).fetch(`https://r/rooms/${room}/record?t=${token}`);
  if (res.status !== 200) return nf();                         // a vanished room looks the same as an unknown token
  return new Response(res.body, { status: 200, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}

async function handleMetrics(request, env, ctx, url) {
  const nope = () => new Response(JSON.stringify({ error: "no" }), { status: 400 });
  if (request.method === "GET" && url.pathname === "/m/report") {
    const ok = env.OPERATOR_TOKEN && await sameToken(request.headers.get("authorization") || "", `Bearer ${env.OPERATOR_TOKEN}`);
    if (!ok) return new Response(JSON.stringify({ error: "not-found" }), { status: 404 });
    return env.COUNTERS.get(env.COUNTERS.idFromName("all")).fetch("https://c/");
  }
  if (request.method !== "POST" || url.pathname !== "/m" || !env.LIMIT_SECRET || !env.COUNTERS) return nope();
  const text = await readCapped(request, MAX_BODY_BYTES);
  if (text === null) return nope();
  const key = beaconKey(text);
  if (!key) return nope();
  const day = dayOf(Date.now());
  const rotating = await clientKey(new Request("https://x/", { headers: { "cf-connecting-ip": request.headers.get("cf-connecting-ip") || "unknown" } }), `${env.LIMIT_SECRET}:${day}`);
  const gate = await env.MLIMIT.get(env.MLIMIT.idFromName(rotating)).fetch("https://limit/");
  if (gate.status === 429) return new Response(JSON.stringify({ error: "slow-down" }), { status: 429 });
  count(env, ctx, key);
  return new Response("{}");
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/m" || url.pathname === "/m/report") return handleMetrics(request, env, ctx, url);
    const rec = url.pathname.match(/^\/records\/([0-9a-f]{32})$/);
    if (rec && request.method === "GET") return handleRecord(env, rec[1]);
    const m = url.pathname.match(/^\/rooms\/([0-9a-f]{32})(\/.*)?$/);
    if (request.method === "POST" && url.pathname === "/rooms") {
      if (!env.LIMIT_SECRET) return new Response(JSON.stringify({ error: "internal" }), { status: 500 });
      const gate = await env.LIMIT.get(env.LIMIT.idFromName(await clientKey(request, env.LIMIT_SECRET))).fetch("https://limit/");
      if (gate.status === 429) return new Response(JSON.stringify({ error: "slow-down" }), { status: 429 });
      const id = crypto.randomUUID().replaceAll("-", "");
      const stub = env.ROOM.get(env.ROOM.idFromName(id));
      const res = await counted(env, ctx, request, "", () => stub.fetch(new Request(`${url.origin}/rooms/${id}`, request)));
      return res.status === 201 ? new Response(JSON.stringify({ id, ...(await res.json()) }), res) : res;
    }
    // Rooms are created only above, behind the limiter; a direct POST to a chosen id must not reach the object.
    if (!m || (!m[2] && request.method !== "GET")) return new Response(JSON.stringify({ error: "not-found" }), { status: 404 });
    return counted(env, ctx, request, m[2] || "", () => env.ROOM.get(env.ROOM.idFromName(m[1])).fetch(request), m[1]);
  },
};
