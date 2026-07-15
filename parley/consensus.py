"""Reach a decision among delegates with conflicting private interests.

The coordinator sees only Verdicts, never the sheets. A decision is valid only if it
is feasible for EVERY agent (all red lines pass). Among those it applies an egalitarian
rule — maximise the least-happy agent's soft score (a Rawlsian / max-min social choice,
not a majority vote), tie-broken by total welfare. No feasible option => honest deadlock.
"""
from dataclasses import dataclass
from typing import Any, Optional

from .transcript import Transcript


@dataclass
class ConsensusResult:
    status: str               # "agreed" | "deadlock"
    decision: Optional[Any]
    transcript: Transcript


def run_consensus(agents, options, rule: str = "egalitarian") -> ConsensusResult:
    transcript = Transcript()
    feasible = []  # (option, floor_score, total_score)

    for option in options:
        verdicts = [a.consider(option) for a in agents]
        transcript.record(option, verdicts)
        if all(v.acceptable for v in verdicts):
            floor = min(v.score for v in verdicts)
            total = sum(v.score for v in verdicts)
            feasible.append((option, floor, total))

    if not feasible:
        transcript.finalize(status="deadlock", decision=None)
        return ConsensusResult("deadlock", None, transcript)

    if rule != "egalitarian":
        raise ValueError(f"unknown rule: {rule!r}")
    # highest floor first, then highest total welfare; stable for reproducibility
    best = max(feasible, key=lambda x: (x[1], x[2]))
    decision = best[0]
    transcript.finalize(status="agreed", decision=decision)
    return ConsensusResult("agreed", decision, transcript)
