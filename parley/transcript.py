"""A tamper-evident record that lets each owner prove their agent was not betrayed.

The transcript holds only public verdicts (never sheets). `hash()` is a deterministic
SHA-256 over the canonical record, so any edit is detectable. `verify_non_betrayal`
lets an owner replay their OWN private sheet against the final decision locally — proving
no red line was crossed without revealing the sheet to anyone.
"""
import hashlib
import json
from typing import Any, Optional

from .preferences import PreferenceSheet


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

    def hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def verify_non_betrayal(self, sheet: PreferenceSheet, decision: Any) -> bool:
        """Replay an owner's private sheet: did the final decision hold all their red lines?"""
        if decision is None:
            return True  # a deadlock forces nothing on anyone
        return sheet.evaluate(decision).feasible
