// HTTP surface over core.mjs. `store` is {get(), put(room)}: a Durable Object's storage in
// production, a Map in tests. Errors carry a code only, never a value (R7).

import { createRoom, join, submit, publicRoom, nonceFor, issuedTokens, RelayError, BAD_CODES } from "./core.mjs";

const MAX_BODY = 64 * 1024;
const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
const err = (code, status = 400) => json({ error: code }, status);

async function body(request) {
  const text = await request.text();
  if (text.length > MAX_BODY) throw new RelayError("too-large");
  try { return JSON.parse(text); } catch { throw new RelayError("bad-json"); }
}

/** path is relative to the room: "", "/join", "/verdicts", "/result" */
export async function handle(request, path, store) {
  try {
    const m = request.method;
    let room = await store.get();
    if (path === "" && m === "POST") {
      if (room) return err("exists", 409);
      const b = await body(request);
      room = createRoom({ options: b.options, owners: b.owners });
      await store.put(room);
      return json({ ...publicRoom(room), tokens: issuedTokens(room) }, 201);
    }
    if (!room) return err("no-room", 404);
    if (path === "" && m === "GET") return json(publicRoom(room));
    if (path === "/join" && m === "POST") {
      const b = await body(request);
      join(room, b.owner, b.pubkey_hex, b.token);
      await store.put(room);
      return json({ session: room.session, nonces: nonceFor(room, b.owner) });
    }
    if (path === "/verdicts" && m === "POST") {
      const b = await body(request);
      try {
        await submit(room, b.owner, b.verdicts);
      } catch (e) {
        if (e instanceof RelayError && BAD_CODES.has(e.code)) await store.put(room); // keep the count
        throw e;
      }
      await store.put(room);
      return json({ done: room.result !== null });
    }
    if (path === "/result" && m === "GET") {
      return room.result ? json(room.result) : err("pending", 425);
    }
    return err("not-found", 404);
  } catch (e) {
    if (e instanceof RelayError) return err(e.code, e.code === "room-closed" ? 409 : e.code === "locked" ? 429 : 400);
    return err("internal", 500);
  }
}

/** One request at a time per room: every handler reads the room, awaits, then writes it back whole,
 *  so two overlapping requests would overwrite each other (a lost verdict, a lost bad-attempt count). */
export function serialHandler() {
  let queue = Promise.resolve();
  return (request, path, store) => {
    const run = queue.then(() => handle(request, path, store));
    queue = run.catch(() => {});
    return run;
  };
}
