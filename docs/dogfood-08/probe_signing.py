"""Signing probe: what Ed25519 verdicts stop, and the two gaps SECURITY.md names (no owner->key roster, no nonce)."""
import copy
import json

from parley.net.identity import Identity, verdict_payload, verify_transcript
from parley.transcript import Transcript

options = [{"id": "a", "cost": 1}, {"id": "b", "cost": 2}]


def signed_transcript(idents, who_signs, accept):
    t = Transcript()
    for o in options:
        verdicts = []
        for owner, ident in idents.items():
            acc = accept(owner, o)
            v = {"owner": owner, "acceptable": acc, "score": 1.0 if acc else 0.0, "reason": "ok" if acc else "red-line"}
            signer = who_signs(owner)
            v["sig"] = signer.sign(verdict_payload(o, owner, acc, v["score"], v["reason"]))
            v["pubkey_hex"] = signer.card().pubkey_hex
            verdicts.append(v)
        t.entries.append({"option": o, "verdicts": verdicts})
    return t


owners = {"Ana": Identity.generate("Ana"), "Bob": Identity.generate("Bob")}
honest = signed_transcript(owners, lambda o: owners[o], lambda o, opt: True)
print(f"{'honest, every verdict signed by its owner':58} {verify_transcript(honest, require_signed=True)}")

t = copy.deepcopy(honest); t.entries[0]["verdicts"][0]["score"] = 0.3
print(f"{'one signed verdict edited':58} {verify_transcript(t, require_signed=True)}")

t = copy.deepcopy(honest); t.entries[0]["verdicts"][0]["sig"] = t.entries[1]["verdicts"][0]["sig"]
print(f"{'a signed verdict moved to another option':58} {verify_transcript(t, require_signed=True)}")

t = copy.deepcopy(honest)
for e in t.entries:
    for v in e["verdicts"]:
        v["sig"] = v["pubkey_hex"] = None
print(f"{'all signatures stripped, default mode':58} {verify_transcript(t)}")
print(f"{'all signatures stripped, require_signed=True':58} {verify_transcript(t, require_signed=True)}")

mallory = Identity.generate("Mallory")
forged = signed_transcript(owners, lambda o: mallory, lambda o, opt: opt["id"] == "b")
print(f"{'coordinator signs EVERY owner verdict with its own key':58} {verify_transcript(forged, require_signed=True)}   <- no roster")
keys = {v["pubkey_hex"] for e in forged.entries for v in e["verdicts"]}
print(f"{'  distinct pubkeys across the two supposed owners':58} {len(keys)}")

# replay: Ana's genuine signed verdict for option a reused in a different parley that has the same option
other = signed_transcript(owners, lambda o: owners[o], lambda o, opt: True)
reused = copy.deepcopy(other)
reused.entries[0]["verdicts"][0] = copy.deepcopy(honest.entries[0]["verdicts"][0])
print(f"{'genuine signed verdict replayed into another parley':58} {verify_transcript(reused, require_signed=True)}   <- no nonce")
