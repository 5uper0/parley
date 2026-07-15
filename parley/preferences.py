"""An owner's private position: hard red lines (must never be crossed) + soft utility.

The hard/soft split is the heart of Parley: red lines are enforced deterministically
in code (a proposal that violates one is *rejected*, never negotiated away), while
soft utility only ranks the options that already clear every red line.
"""
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class HardConstraint:
    """A named red line. `predicate(option) is True` means the option is acceptable."""
    name: str
    predicate: Callable[[Any], bool]


@dataclass(frozen=True)
class Evaluation:
    feasible: bool          # all hard constraints pass
    violated: list          # names of crossed red lines (stays private to the owner)
    score: float            # soft utility in [0, 1]


class PreferenceSheet:
    def __init__(
        self,
        owner: str,
        hard: Optional[list] = None,
        utility: Optional[Callable[[Any], float]] = None,
    ):
        self.owner = owner
        self.hard = list(hard) if hard else []
        self.utility = utility

    def evaluate(self, option: Any) -> Evaluation:
        violated = [c.name for c in self.hard if not c.predicate(option)]
        if self.utility is None:
            score = 0.5  # neutral when the owner expressed no soft preference
        else:
            score = max(0.0, min(1.0, float(self.utility(option))))
        return Evaluation(feasible=not violated, violated=violated, score=score)
