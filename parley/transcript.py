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


class Transcript:
    def __init__(self):
        self.entries = []              # [{"option":..., "verdicts":[{owner,acceptable,score,reason}]}]
        self.result: Optional[dict] = None

    def record(self, option: Any, verdicts) -> None:
        self.entries.append({
            "option": option,
            "verdicts": [
                {"owner": v.owner, "acceptable": v.acceptable, "score": v.score,
                 "reason": v.reason, "sig": v.sig, "pubkey_hex": v.pubkey_hex}
                for v in verdicts
            ],
        })

    def finalize(self, status: str, decision: Any) -> None:
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
        blob = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def verify_non_betrayal(self, sheet: PreferenceSheet, decision: Any) -> bool:
        """Replay an owner's private sheet: did the final decision hold all their red lines?"""
        if decision is None:
            return True  # a deadlock forces nothing on anyone
        return sheet.evaluate(decision).feasible
