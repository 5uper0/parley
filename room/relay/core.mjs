// Relay logic with no platform code: pure functions over a plain-JSON room state, so the same
// code runs in Node tests and inside a Cloudflare Durable Object. The relay never receives a
// sheet or an answer. It sees an option list, public keys, and signed masked verdicts.
// Mirrors parley/net/identity.py (verdict/0.2 payload, R1 roster pin, R2 session+nonce).

import { canonicalJson, Fl, chooseFromEntries, sha256Hex } from "../engine.mjs";

const HEX = /^[0-9a-f]+$/;
const MAX_OPTIONS = 8, MAX_OWNERS = 12, MAX_NAME = 64;
export const BAD_LIMIT = 5, BAD_WINDOW_MS = 10 * 60 * 1000; // P2: per owner, decays; a link holder can slow one owner, never freeze the room
export const ROOM_TTL_MS = 30 * 24 * 3600 * 1000; // answers' verdicts are deleted this long after creation

export class RelayError extends Error {
  constructor(code) { super(code); this.code = code; }
}
const fail = (code) => { throw new RelayError(code); };

const hexToBytes = (h) => Uint8Array.from(h.match(/../g) || [], (b) => parseInt(b, 16));
const bytesToHex = (b) => Array.from(new Uint8Array(b), (x) => x.toString(16).padStart(2, "0")).join("");

export function randomHex(n = 16) {
  return bytesToHex(globalThis.crypto.getRandomValues(new Uint8Array(n)));
}

/** The exact bytes a device signs for one verdict (type verdict/0.2). */
export function verdictPayload({ option, owner, acceptable, score, reason, session, nonce }) {
  return new TextEncoder().encode(canonicalJson({
    type: "verdict/0.2", owner, option, acceptable, score: new Fl(score), reason, session, nonce,
  }));
}

async function verifySig(pubkeyHex, payload, sigHex) {
  try {
    const key = await globalThis.crypto.subtle.importKey(
      "raw", hexToBytes(pubkeyHex), { name: "Ed25519" }, false, ["verify"]);
    return await globalThis.crypto.subtle.verify({ name: "Ed25519" }, key, hexToBytes(sigHex), payload);
  } catch { return false; }
}

const isHex = (s, len) => typeof s === "string" && s.length === len && HEX.test(s);
const isName = (s) => typeof s === "string" && s.length > 0 && s.length <= MAX_NAME;

/** options: non-empty list of JSON objects; owners: distinct names. Option set is fixed here (R4). */
export function createRoom({ options, owners }) {
  if (!Array.isArray(options) || options.length < 1 || options.length > MAX_OPTIONS) fail("bad-options");
  if (!Array.isArray(owners) || owners.length < 2 || owners.length > MAX_OWNERS
      || !owners.every(isName) || new Set(owners).size !== owners.length
      || owners.some((o) => o in {})) fail("bad-owners"); // "constructor", "__proto__" and friends would hit Object.prototype
  const optionKeys = options.map((o) => {
    if (o === null || typeof o !== "object" || Array.isArray(o)) fail("bad-options");
    try { return canonicalJson(o); } catch { return fail("bad-options"); }
  });
  if (new Set(optionKeys).size !== optionKeys.length) fail("bad-options");
  return {
    session: randomHex(16), options, owners: [...owners],
    nonces: Object.fromEntries(owners.map((o) => [o, options.map(() => randomHex(12))])), // unique per verdict
    tokens: Object.fromEntries(owners.map((o) => [o, randomHex(16)])), // each person's link carries theirs; /join needs it
    roster: {},            // owner -> pubkey_hex, pinned at join
    verdicts: {},          // owner -> [ {acceptable, score, reason, sig} per option ]
    result: null, badStamps: {}, // owner -> timestamps of rejected submissions
  };
}

/** Sliding-window limiter over a plain JSON list of timestamps (ms). Returns the new list or null if over. */
export function rateAllow(stamps, now, limit, windowMs) {
  const live = stamps.filter((t) => now - t < windowMs);
  if (live.length >= limit) return null;
  return [...live, now];
}

/** Public view for a joining device: what to sign, never anything about other people's answers. */
export function publicRoom(room) {
  return { session: room.session, options: room.options, owners: room.owners,
           joined: Object.keys(room.roster),
           submitted: Object.keys(room.verdicts), done: room.result !== null };
}

/** What one device needs to sign: its own nonces only. */
export function nonceFor(room, owner) {
  if (!room.owners.includes(owner)) fail("unknown-owner");
  return room.nonces[owner];
}

/** The tokens are shown once, in the creation response; publicRoom never carries them. */
export function issuedTokens(room) { return { ...room.tokens }; }

export function join(room, owner, pubkeyHex, token) {
  if (!room.owners.includes(owner)) fail("unknown-owner");
  if (typeof token !== "string" || token !== room.tokens[owner]) fail("bad-token"); // knowing a name is not enough to take a seat
  if (!isHex(pubkeyHex, 64)) fail("bad-key");
  const key = pubkeyHex.toLowerCase();
  if (room.roster[owner]) fail("already-joined");           // R1: one key per owner, pinned once
  if (Object.values(room.roster).includes(key)) fail("key-reused"); // one key may not stand for two owners
  room.roster[owner] = key;
}

/** verdicts: one per option, in option order: {acceptable, score, reason, sig}. */
export const BAD_CODES = new Set(["bad-signature", "bad-verdicts"]);

export async function submit(room, owner, verdicts, now = Date.now()) {
  if (room.result) fail("room-closed");
  const live = (room.badStamps[owner] || []).filter((t) => now - t < BAD_WINDOW_MS);
  if (live.length >= BAD_LIMIT) fail("locked");
  try {
    await submitChecked(room, owner, verdicts);
  } catch (e) {
    if (e instanceof RelayError && BAD_CODES.has(e.code)) room.badStamps[owner] = [...live, now];
    throw e;
  }
}

async function submitChecked(room, owner, verdicts) {
  const key = room.roster[owner];
  if (!key) fail("not-joined");
  if (room.verdicts[owner]) fail("already-submitted");
  if (!Array.isArray(verdicts) || verdicts.length !== room.options.length) fail("bad-verdicts");
  for (let i = 0; i < verdicts.length; i++) {
    const v = verdicts[i];
    if (!v || typeof v.acceptable !== "boolean" || typeof v.score !== "number"
        || !Number.isFinite(v.score) || v.score < 0 || v.score > 1
        || (!v.acceptable && v.score !== 0) || v.reason !== (v.acceptable ? "ok" : "red-line") || !isHex(v.sig, 128)) fail("bad-verdicts");
    const payload = verdictPayload({ option: room.options[i], owner, acceptable: v.acceptable,
      score: v.score, reason: v.reason, session: room.session, nonce: room.nonces[owner][i] });
    if (!(await verifySig(key, payload, v.sig))) fail("bad-signature");
  }
  room.verdicts[owner] = verdicts.map(({ acceptable, score, reason, sig }) => ({ acceptable, score, reason, sig }));
  if (room.owners.every((o) => room.verdicts[o])) await finish(room);
}

async function finish(room) {
  const entries = room.options.map((option, i) => ({
    option,
    verdicts: room.owners.map((o) => {
      const v = room.verdicts[o][i];
      return { owner: o, acceptable: v.acceptable, score: v.score, reason: v.reason,
               sig: v.sig, pubkey_hex: room.roster[o], session: room.session, nonce: room.nonces[o][i] };
    }),
  }));
  const result = chooseFromEntries(entries);
  const record = {
    entries: entries.map((e) => ({ option: e.option,
      verdicts: e.verdicts.map((v) => ({ ...v, score: new Fl(v.score) })) })),
    result: { status: result.status, decision: result.decision },
  };
  // A string, not an object: JSON.stringify would turn 1.0 into 1 and break the hash for any verifier.
  const transcriptJson = canonicalJson(record);
  room.result = { ...result, transcript_json: transcriptJson, transcript_hash: await sha256Hex(transcriptJson),
                  roster: { ...room.roster }, session: room.session };
}
