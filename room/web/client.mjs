// Device side of the Room: key, join, sign, submit, poll. `fetchFn` is injected so the same code
// runs in a browser, in Node tests, and against room/relay/http.mjs without a network.

import { verdictFor } from "../engine.mjs";
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
  return r.data; // {id, session, options, owners, ...}
}

export async function joinRoom(fetchFn, base, roomId, owner, device) {
  const r = await call(fetchFn, base, "POST", `/rooms/${roomId}/join`, { owner, pubkey_hex: device.pubkeyHex });
  if (!r.ok) throw new Error(r.data.error);
  return r.data; // {session, nonces}
}

/** Apply the private sheet to every option on this device, sign, send only the masked verdicts. */
export async function submitAnswers(fetchFn, base, roomId, { owner, sheet, options, session, nonces, device }) {
  const verdicts = [];
  for (let i = 0; i < options.length; i++) {
    const v = verdictFor(sheet, options[i]);
    const payload = verdictPayload({ option: options[i], owner, acceptable: v.acceptable, score: v.score,
                                     reason: v.reason, session, nonce: nonces[i] });
    const sig = toHex(await globalThis.crypto.subtle.sign({ name: "Ed25519" }, device.privateKey, payload));
    verdicts.push({ acceptable: v.acceptable, score: v.score, reason: v.reason, sig });
  }
  const r = await call(fetchFn, base, "POST", `/rooms/${roomId}/verdicts`, { owner, verdicts });
  if (!r.ok) throw new Error(r.data.error);
  return r.data;
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
