// Device side of the Room: key, join, sign, submit, poll. `fetchFn` is injected so the same code
// runs in a browser, in Node tests, and against room/relay/http.mjs without a network.

import { verdictFor, chooseFromEntries, canonicalJson, sha256Hex } from "../engine.mjs";
import { verdictPayload } from "../relay/core.mjs";

const toHex = (buf) => Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");

export async function newDevice() {
  const kp = await globalThis.crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  return { privateKey: kp.privateKey, pubkeyHex: toHex(await globalThis.crypto.subtle.exportKey("raw", kp.publicKey)),
           privateJwk: await globalThis.crypto.subtle.exportKey("jwk", kp.privateKey) };
}

/** Restore a device after a page reload from the saved JWK (kept in this browser only). */
export async function restoreDevice(privateJwk) {
  const privateKey = await globalThis.crypto.subtle.importKey("jwk", privateJwk, { name: "Ed25519" }, true, ["sign"]);
  const raw = Uint8Array.from(atob(privateJwk.x.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
  return { privateKey, pubkeyHex: toHex(raw), privateJwk };
}

async function call(fetchFn, base, method, path, body) {
  const res = await fetchFn(`${base}${path}`, { method, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function createRoom(fetchFn, base, { options, owners }) {
  const r = await call(fetchFn, base, "POST", "/rooms", { options, owners });
  if (!r.ok) throw new Error(r.data.error);
  return r.data; // {id, session, options, owners, tokens: {owner: token}, ...}
}

/** The creator's key lives in the tab's sessionStorage only: never in a URL, a log or localStorage. */
const orgKey = (roomId) => `parley-org-${roomId}`;
export const saveOrganizerKey = (storage, roomId, key) => { if (/^[0-9a-f]{32}$/.test(key || "")) storage.setItem(orgKey(roomId), key); };
export const loadOrganizerKey = (storage, roomId) => storage.getItem(orgKey(roomId));

/** Lost phone: the creator gets a new token for one unsubmitted seat. The old link stops working. */
export async function reissueSeat(fetchFn, base, roomId, organizerKey, owner) {
  const r = await call(fetchFn, base, "POST", `/rooms/${roomId}/reissue`, { organizer_key: organizerKey, owner });
  if (!r.ok) throw new Error(r.data.error);
  if (!/^[0-9a-f]{32}$/.test(r.data.token || "")) throw new Error("bad-token"); // a relay can send anything
  return r.data.token;
}

export async function joinRoom(fetchFn, base, roomId, owner, device, token) {
  const r = await call(fetchFn, base, "POST", `/rooms/${roomId}/join`, { owner, pubkey_hex: device.pubkeyHex, token });
  if (!r.ok) throw new Error(r.data.error);
  return r.data; // {session, nonces}
}

/** Apply the private sheet to every option on this device and sign. Done once: the result is what gets
 *  saved and resent on a retry, never signed a second time under the same nonces. */
export async function signAnswers({ owner, sheet, options, owners, session, nonces, device }) {
  const verdicts = [];
  for (let i = 0; i < options.length; i++) {
    const v = verdictFor(sheet, options[i]);
    const payload = verdictPayload({ option: options[i], owner, acceptable: v.acceptable, score: v.score,
                                     reason: v.reason, session, nonce: nonces[i] });
    const sig = toHex(await globalThis.crypto.subtle.sign({ name: "Ed25519" }, device.privateKey, payload));
    verdicts.push({ acceptable: v.acceptable, score: v.score, reason: v.reason, sig });
  }
  return { owner, owners, session, nonces, options, verdicts, pubkeyHex: device.pubkeyHex };
}

/** Send only the masked verdicts. */
export async function postAnswers(fetchFn, base, roomId, sent) {
  const r = await call(fetchFn, base, "POST", `/rooms/${roomId}/verdicts`, { owner: sent.owner, verdicts: sent.verdicts });
  if (!r.ok) throw new Error(r.data.error);
  return r.data;
}

export async function submitAnswers(fetchFn, base, roomId, args) {
  const sent = await signAnswers({ ...args, owners: args.owners ?? [] });
  const data = await postAnswers(fetchFn, base, roomId, sent);
  return { ...data, sent };
}

export async function getStatus(fetchFn, base, roomId) {
  const r = await call(fetchFn, base, "GET", `/rooms/${roomId}`);
  if (!r.ok) throw new Error(r.data.error);
  return r.data;
}

/** null while waiting; the result once every person has submitted. */
export async function getResult(fetchFn, base, roomId) {
  const r = await call(fetchFn, base, "GET", `/rooms/${roomId}/result`);
  if (r.status === 425) return null;
  if (!r.ok) throw new Error(r.data.error);
  return r.data;
}

/** The room's names, fixed by the organizer into every person's link: the relay cannot add or drop a seat unseen. */
export async function rosterHash(owners) {
  return (await sha256Hex(canonicalJson([...owners].sort()))).slice(0, 32);
}

/** Join-screen check: the room the relay describes must be the one the link and the page describe. */
export async function checkRoom(status, linkRosterHash, pageOptions) {
  return (await rosterHash(status.owners)) === linkRosterHash && canonicalJson(status.options) === canonicalJson(pageOptions);
}

/** Do not trust the relay: re-derive everything a person can check from the record itself.
 *  `sent` (optional) is what this device submitted; with it, the record must carry exactly that. */
export async function verifyResult(result, sent, expected) {
  if (!expected?.options || !expected?.rosterHash) throw new Error("verifyResult needs the page's options and the link's roster hash");
  const bad = (why) => ({ ok: false, why });
  let rec;
  try { rec = JSON.parse(result.transcript_json); } catch { return bad("record"); }
  if (await sha256Hex(result.transcript_json) !== result.transcript_hash) return bad("hash");
  const entries = rec.entries;
  if (!Array.isArray(entries) || !entries.length) return bad("record");
  const seenNonces = new Set();
  const keyOf = {};
  const rosterOwners = Object.keys(result.roster).sort();
  // who was in the room is known to this phone from before it answered; a relay cannot shrink the room afterwards
  if (await rosterHash(rosterOwners) !== expected.rosterHash) return bad("owners");
  if (sent?.owners?.length && canonicalJson([...sent.owners].sort()) !== canonicalJson(rosterOwners)) return bad("owners");
  for (const e of entries) {
    // one verdict from every owner on every option: a missing red-line would turn a veto into an "agreement"
    if (canonicalJson(e.verdicts.map((v) => v.owner).sort()) !== canonicalJson(rosterOwners)) return bad("incomplete");
    for (const v of e.verdicts) {
      if (v.session !== result.session || seenNonces.has(v.nonce)) return bad("session");
      seenNonces.add(v.nonce);
      if (result.roster[v.owner] !== v.pubkey_hex || (keyOf[v.owner] ??= v.pubkey_hex) !== v.pubkey_hex) return bad("roster");
      const payload = verdictPayload({ option: e.option, owner: v.owner, acceptable: v.acceptable, score: v.score,
                                       reason: v.reason, session: v.session, nonce: v.nonce });
      if (!(await verifyEd25519(v.pubkey_hex, payload, v.sig))) return bad("signature");
    }
  }
  // the option list is the template this page ships, never the relay's say-so
  if (canonicalJson(entries.map((e) => e.option)) !== canonicalJson(expected.options)) return bad("options");
  const redo = chooseFromEntries(entries);
  if (redo.status !== result.status || canonicalJson(redo.decision) !== canonicalJson(result.decision)) return bad("decision");
  if (rec.result.status !== redo.status || canonicalJson(rec.result.decision) !== canonicalJson(redo.decision)) return bad("decision");
  if (sent) {
    if (result.session !== sent.session || result.roster[sent.owner] !== sent.pubkeyHex) return bad("mine");
    if (canonicalJson(entries.map((e) => e.option)) !== canonicalJson(sent.options)) return bad("mine");
    for (let i = 0; i < entries.length; i++) {
      const mine = entries[i].verdicts.find((v) => v.owner === sent.owner);
      const s = sent.verdicts[i];
      if (!mine || mine.sig !== s.sig || mine.acceptable !== s.acceptable || mine.score !== s.score
          || mine.nonce !== sent.nonces[i]) return bad("mine");
    }
  }
  return { ok: true };
}

async function verifyEd25519(pubHex, payload, sigHex) {
  try {
    const bytes = (h) => Uint8Array.from(h.match(/../g) || [], (b) => parseInt(b, 16));
    const key = await globalThis.crypto.subtle.importKey("raw", bytes(pubHex), { name: "Ed25519" }, false, ["verify"]);
    return await globalThis.crypto.subtle.verify({ name: "Ed25519" }, key, bytes(sigHex), payload);
  } catch { return false; }
}

/** Is a record-page response well formed? A malicious relay can send anything; unknown decision ids and prototype keys fail. */
export function recordShapeOk(r, knownOptionIds) {
  if (!r || typeof r !== "object" || !Array.isArray(r.owners) || !r.owners.every((o) => typeof o === "string")) return false;
  if (typeof r.transcript_hash !== "string" || !/^[0-9a-f]{64}$/.test(r.transcript_hash)) return false;
  if (r.status === "deadlock") return true;
  return r.status === "agreed" && typeof r.decision?.id === "string" && Object.hasOwn(knownOptionIds, r.decision.id);
}
