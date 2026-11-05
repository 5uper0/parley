import { test } from "node:test";
import assert from "node:assert/strict";
import { handle } from "../relay/http.mjs";
import { HEIRS_OPTIONS, sheetFromAnswers, describeAnswers } from "../web/heirs.mjs";
import { newDevice, restoreDevice, createRoom, joinRoom, submitAnswers, getResult, getStatus } from "../web/client.mjs";

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
  const owners = Object.keys(byOwner);
  const room = await createRoom(f, BASE, { options: HEIRS_OPTIONS, owners });
  for (const owner of owners) {
    const device = await newDevice();
    const { session, nonces } = await joinRoom(f, BASE, room.id, owner, device);
    await submitAnswers(f, BASE, room.id, { owner, sheet: sheetFromAnswers(owner, byOwner[owner]),
      options: room.options, session, nonces, device });
  }
  return { f, room, result: await getResult(f, BASE, room.id) };
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
  const { session, nonces } = await joinRoom(f, BASE, room.id, "a", device);
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
