"""Reach a decision among delegates with conflicting private interests.

The coordinator sees only Verdicts, never the sheets. A decision is valid only if it
is feasible for EVERY agent (all red lines pass). Among those it applies an egalitarian
rule — maximise the least-happy agent's soft score (a Rawlsian / max-min social choice,
not a majority vote), tie-broken by total welfare. No feasible option => honest deadlock.
"""
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Protocol, Sequence, Tuple

from .agent import Verdict
from .transcript import Transcript


class AgentLike(Protocol):
    """What run_consensus needs from a delegate: local Agent and net.client.RemoteAgent
    both satisfy this structurally, without either importing the other."""
    owner: str

    def consider(self, option: Any) -> Verdict: ...


@dataclass
class ConsensusResult:
    status: str               # "agreed" | "deadlock"
    decision: Optional[Any]
    transcript: Transcript


def run_consensus(
    agents: Sequence[AgentLike], options: Sequence[Any], rule: str = "egalitarian"
) -> ConsensusResult:
    if rule != "egalitarian":
        raise ValueError(f"unknown rule: {rule!r}")
    owners = [a.owner for a in agents]
    if len(set(owners)) != len(owners):
        raise ValueError("owner names must be distinct")
    transcript = Transcript()
    feasible: List[Tuple[Any, float, float]] = []  # (option, floor_score, total_score)

    for option in options:
        verdicts = [a.consider(option) for a in agents]
        transcript.record(option, verdicts)
        if verdicts and all(v.acceptable for v in verdicts):
            floor = min(v.score for v in verdicts)
            total = sum(v.score for v in verdicts)
            feasible.append((option, floor, total))

    if not feasible:
        transcript.finalize(status="deadlock", decision=None)
        return ConsensusResult("deadlock", None, transcript)

    # highest floor first, then highest total welfare; stable for reproducibility
    best = max(feasible, key=lambda x: (x[1], x[2]))
    decision = best[0]
    transcript.finalize(status="agreed", decision=decision)
    return ConsensusResult("agreed", decision, transcript)


def verify_outcome(transcript: Transcript, *,
                   expected_owners: Optional[Iterable[str]] = None) -> bool:
    """Recompute the max-min outcome from the transcript's recorded verdicts and check it matches
    the announced decision. This is what catches a dishonest coordinator that finalized a
    *feasible-but-not-max-min* option (or an infeasible one): `verify_non_betrayal` only proves an
    owner's *own* red lines held, never that the selection itself was computed honestly. Anyone can
    replay this over the public record — no private sheet needed.

    Every entry must carry exactly one verdict from each owner in the record. Without that, a
    coordinator could drop one owner's veto from the entry it wants to win (or duplicate another
    owner's verdict in its place) and the recomputation would agree with it.

    That check is relative to the record itself, so a coordinator that drops one owner from
    *every* entry (or the lone veto in a one-option record) still passes it. Pass
    `expected_owners`, the roster the caller expects, and every entry's owner set must equal it
    exactly. The check is only as good as that roster: taken from the same coordinator that
    wrote the record, it binds nothing.
    """
    feasible: List[Tuple[Any, float, float]] = []
    roster = None if expected_owners is None else sorted(expected_owners)
    for entry in transcript.entries:
        verdicts = entry["verdicts"]
        owners = sorted(v["owner"] for v in verdicts)
        if len(set(owners)) != len(owners) or (roster is not None and owners != roster):
            return False
        roster = owners
        if verdicts and all(v["acceptable"] for v in verdicts):
            floor = min(v["score"] for v in verdicts)
            total = sum(v["score"] for v in verdicts)
            feasible.append((entry["option"], floor, total))
    result = transcript.result or {}
    if not feasible:
        return result.get("status") == "deadlock" and result.get("decision") is None
    best = max(feasible, key=lambda x: (x[1], x[2]))
    return result.get("status") == "agreed" and result.get("decision") == best[0]
