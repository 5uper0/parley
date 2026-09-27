"""A tamper-evident record that lets each owner prove their agent was not betrayed.

The transcript holds only public verdicts (never sheets). `hash()` is a deterministic
SHA-256 over the canonical record, so any edit is detectable. `verify_non_betrayal`
lets an owner replay their OWN private sheet against the final decision locally — proving
no red line was crossed without revealing the sheet to anyone.
"""
import copy
import hashlib
import json
from typing import Any, Optional

from .preferences import PreferenceSheet

_VERDICT_KEYS = frozenset({"owner", "acceptable", "score", "reason", "sig", "pubkey_hex"})


_TUPLE_TAG = "__tuple__"


def _tag_tuples(obj: Any) -> Any:
    """`json.dumps` encodes a tuple the same way as a list, so `(1, 2)` and `[1, 2]` used to hash
    (and sign) identically — two different records, one hash. Recursively mark a tuple before it
    reaches `json.dumps`; a structure with no tuple in it serializes to the exact same bytes as
    before, so every hash already on record for a JSON-native option is unaffected.

    A plain dict `{"__tuple__": [...]}` is JSON an untrusted coordinator can send over the wire,
    with no live Python tuple involved; letting it canonicalize to the same bytes as the tag
    would trade the collision being fixed for a worse one. Refuse it instead, the same way a
    value `json.dumps` itself cannot encode is refused."""
    if isinstance(obj, tuple):
        return {_TUPLE_TAG: [_tag_tuples(v) for v in obj]}
    if isinstance(obj, list):
        return [_tag_tuples(v) for v in obj]
    if isinstance(obj, dict):
        if _TUPLE_TAG in obj:
            raise TypeError(f"a dict key {_TUPLE_TAG!r} is reserved for the tuple/list canonicalization")
        return {k: _tag_tuples(v) for k, v in obj.items()}
    return obj


def canonical_json(obj: Any) -> str:
    """The one encoding every hash and every signed payload in this package uses."""
    return json.dumps(_tag_tuples(obj), sort_keys=True, ensure_ascii=False)


class Transcript:
    def __init__(self):
        self.entries = []              # [{"option":..., "verdicts":[{owner,acceptable,score,reason}]}]
        self.result: Optional[dict] = None

    def record(self, option: Any, verdicts) -> None:
        canonical_json(option)
        self.entries.append({
            "option": option,
            "verdicts": [
                {"owner": v.owner, "acceptable": v.acceptable, "score": v.score,
                 "reason": v.reason, "sig": v.sig, "pubkey_hex": v.pubkey_hex}
                for v in verdicts
            ],
        })

    def finalize(self, status: str, decision: Any) -> None:
        canonical_json(decision)
        self.result = {"status": status, "decision": decision}

    def to_dict(self) -> dict:
        return {"entries": self.entries, "result": self.result}

    @classmethod
    def from_dict(cls, data: Any) -> "Transcript":
        """Rebuild a record from `to_dict()` output so its hash can be re-derived by someone
        who was not in the room. Shape is checked strictly and fails closed: a key `record()`
        never writes would either ride into the hash unseen or be silently dropped, and both
        make the re-derived digest mean something other than "this is that record"."""
        if not isinstance(data, dict) or set(data) != {"entries", "result"}:
            raise ValueError("transcript must be an object with exactly 'entries' and 'result'")
        entries, result = data["entries"], data["result"]
        if not isinstance(entries, list):
            raise ValueError("transcript 'entries' must be a list")
        if result is not None and (
                not isinstance(result, dict) or set(result) != {"status", "decision"}):
            raise ValueError("transcript 'result' must be null or {status, decision}")
        t = cls()
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict) or set(entry) != {"option", "verdicts"}:
                raise ValueError(f"entry {i} must be {{option, verdicts}}")
            if not isinstance(entry["verdicts"], list):
                raise ValueError(f"entry {i} 'verdicts' must be a list")
            verdicts = []
            for j, v in enumerate(entry["verdicts"]):
                if not isinstance(v, dict) or set(v) != _VERDICT_KEYS:
                    raise ValueError(f"entry {i} verdict {j} must carry exactly {sorted(_VERDICT_KEYS)}")
                verdicts.append({k: copy.deepcopy(v[k]) for k in _VERDICT_KEYS})
            t.entries.append({"option": copy.deepcopy(entry["option"]), "verdicts": verdicts})
        t.result = copy.deepcopy(result)
        return t

    def hash(self) -> str:
        blob = canonical_json(self.to_dict())
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def verify_non_betrayal(self, sheet: PreferenceSheet, decision: Any) -> bool:
        """Replay an owner's private sheet: did the final decision hold all their red lines?"""
        if decision is None:
            return True  # a deadlock forces nothing on anyone
        return sheet.evaluate(decision).feasible
