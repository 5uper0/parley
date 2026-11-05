// Cloudflare Worker entry. One Durable Object per room; its id is the secret room link.
// The relay holds an option list, public keys and signed masked verdicts. Never sheets.

import { serialHandler } from "./http.mjs";
import { rateAllow, ROOM_TTL_MS } from "./core.mjs";

const ROOMS_PER_HOUR = 20;

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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const m = url.pathname.match(/^\/rooms\/([0-9a-f]{32})(\/.*)?$/);
    if (request.method === "POST" && url.pathname === "/rooms") {
      if (!env.LIMIT_SECRET) return new Response(JSON.stringify({ error: "internal" }), { status: 500 });
      const gate = await env.LIMIT.get(env.LIMIT.idFromName(await clientKey(request, env.LIMIT_SECRET))).fetch("https://limit/");
      if (gate.status === 429) return new Response(JSON.stringify({ error: "slow-down" }), { status: 429 });
      const id = crypto.randomUUID().replaceAll("-", "");
      const stub = env.ROOM.get(env.ROOM.idFromName(id));
      const res = await stub.fetch(new Request(`${url.origin}/rooms/${id}`, request));
      return res.status === 201 ? new Response(JSON.stringify({ id, ...(await res.json()) }), res) : res;
    }
    // Rooms are created only above, behind the limiter; a direct POST to a chosen id must not reach the object.
    if (!m || (!m[2] && request.method !== "GET")) return new Response(JSON.stringify({ error: "not-found" }), { status: 404 });
    return env.ROOM.get(env.ROOM.idFromName(m[1])).fetch(request);
  },
};
