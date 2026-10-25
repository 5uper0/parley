"""A delegate that faithfully represents one owner without leaking the owner's sheet.

The only thing that ever leaves an agent is a Verdict: acceptable + a soft score +
a *masked* reason. It never says which red line was crossed, and never exposes the
PreferenceSheet. Non-betrayal is a code-enforced property, not an LLM's discretion.

A red-lined verdict carries the constant score 0.0, not the real one. Max-min only ranks
options every agent accepts, so the real score of a rejected option never affects a decision;
publishing it only leaked preference data (a utility scaled to a budget gives the budget away).
"""
from dataclasses import dataclass
from typing import Any, Optional

from .preferences import PreferenceSheet


@dataclass(frozen=True)
class Verdict:
    owner: str
    acceptable: bool
    score: float
    reason: str  # "ok" | "red-line"  (masked — never names the constraint)
    # optional signature layer (filled by remote/signed bots; None for local agents).
    # plain strings so the zero-dependency core never imports the crypto lib.
    sig: Optional[str] = None
    pubkey_hex: Optional[str] = None


class Agent:
    def __init__(self, owner: str, sheet: PreferenceSheet):
        self.owner = owner
        self.sheet = sheet  # private; never handed to the coordinator

    def consider(self, option: Any) -> Verdict:
        ev = self.sheet.evaluate(option)
        return Verdict(
            owner=self.owner,
            acceptable=ev.feasible,
            score=ev.score if ev.feasible else 0.0,
            reason="ok" if ev.feasible else "red-line",
        )
