// Prints one relay result as JSON so the Python test can verify it with parley's own verifier.
import { createRoom, join, submit, verdictPayload } from "../relay/core.mjs";
import { verdictFor } from "../engine.mjs";

const sheets = {
  ana: { owner: "ana", hard: [{ attr: "slot", op: "!=", value: "sun" }], utility: [] },
  ben: { owner: "ben", hard: [], utility: [{ attr: "slot", prefer: "sat", weight: 1 }] },
};
const room = createRoom({ options: [{ slot: "sat" }, { slot: "sun" }], owners: ["ana", "ben"] });
const hex = (b) => Array.from(new Uint8Array(b), (x) => x.toString(16).padStart(2, "0")).join("");
for (const owner of ["ana", "ben"]) {
  const kp = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  join(room, owner, hex(await crypto.subtle.exportKey("raw", kp.publicKey)), room.tokens[owner]);
  const vs = [];
  for (let i = 0; i < room.options.length; i++) {
    const v = verdictFor(sheets[owner], room.options[i]);
    const payload = verdictPayload({ option: room.options[i], owner, acceptable: v.acceptable, score: v.score,
      reason: v.reason, session: room.session, nonce: room.nonces[owner][i] });
    vs.push({ acceptable: v.acceptable, score: v.score, reason: v.reason,
              sig: hex(await crypto.subtle.sign({ name: "Ed25519" }, kp.privateKey, payload)) });
  }
  await submit(room, owner, vs);
}
console.log(JSON.stringify(room.result));
