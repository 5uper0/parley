"""Declarative decision recipes — constraints as *data*, not Python.

A `DecisionSpec` describes options + each party's red lines and preferences as plain data, so a
recipe is shareable/importable JSON and never executable code (a gallery can't ship a backdoor).
This module *compiles* that declarative form into the existing engine — `PreferenceSheet`,
`Agent`, `run_consensus` — which stays unchanged. Zero-dependency: stdlib only.
"""
import math
from dataclasses import dataclass, field
from typing import Any, Optional

from .agent import Agent
from .consensus import run_consensus
from .preferences import HardConstraint, PreferenceSheet

_MISSING = object()


def _same_kind(a: Any, b: Any) -> bool:
    """True/False must not equal 1/0: a red line `reviewed == true` is not met by `1`."""
    return isinstance(a, bool) == isinstance(b, bool)


def _strict_eq(a: Any, b: Any) -> bool:
    """Equality that keeps bool apart from int at every depth, so `[True]` is not `[1]`."""
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_strict_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_strict_eq(a[k], b[k]) for k in a)
    return _same_kind(a, b) and a == b


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_options(options: list) -> None:
    """Fail loudly at load: duplicate ids and non-finite numbers would otherwise show up as a
    silent deadlock or a poisoned score."""
    seen = set()
    for opt in options:
        if isinstance(opt, dict):
            if "id" in opt:
                if opt["id"] in seen:
                    raise ValueError(f"duplicate option id: {opt['id']!r}")
                seen.add(opt["id"])
            for key, val in opt.items():
                if isinstance(val, float) and not math.isfinite(val):
                    raise ValueError(f"non-finite number in option {opt.get('id')!r}, attribute {key!r}")


@dataclass(frozen=True)
class Constraint:
    """A red line as data: `option[attr] <op> value` must hold, else the option is rejected.

    Missing attribute → fails closed (option not acceptable): a recipe should carry every attr
    its constraints reference.
    """
    attr: str
    op: str
    value: Any

    def check(self, option: dict) -> bool:
        val = option.get(self.attr, _MISSING)
        if val is _MISSING:
            return False
        op = self.op
        if op == "==":     return _strict_eq(val, self.value)
        if op == "!=":
            if val == self.value and not _strict_eq(val, self.value):
                return False  # 0 is not "not false": a type confusion must not slip past a negative line
            return not (val == self.value)
        if op in ("<", "<=", ">", ">="):
            if not (_is_number(val) and _is_number(self.value)):
                return False  # fail closed: booleans and non-numbers are not ordered
            if op == "<":  return val < self.value
            if op == "<=": return val <= self.value
            if op == ">":  return val > self.value
            return val >= self.value
        if op == "in":     return any(_strict_eq(val, v) for v in self.value)
        if op == "not_in":
            if any(val == v and not _strict_eq(val, v) for v in self.value):
                return False
            return not any(val == v for v in self.value)
        raise ValueError(f"unknown operator: {self.op!r}")

    def describe(self) -> str:
        return f"{self.attr} {self.op} {self.value!r}"

    def to_dict(self) -> dict:
        return {"attr": self.attr, "op": self.op, "value": self.value}

    @classmethod
    def from_dict(cls, d: dict) -> "Constraint":
        op, value = d["op"], d["value"]
        if op in ("in", "not_in") and not isinstance(value, list):
            raise ValueError(f"operator {op!r} needs a list value")
        if op in ("<", "<=", ">", ">=") and not _is_number(value):
            raise ValueError(f"operator {op!r} needs a number, not booleans or text")
        return cls(attr=d["attr"], op=op, value=value)


@dataclass(frozen=True)
class UtilityTerm:
    """One soft-preference term. Either categorical (`prefer` a value) or numeric (`direction`
    "higher"/"lower", normalized on `[lo, hi]`). Contribution is weighted; a party's score is the
    weighted average across its terms, clamped to [0, 1]."""
    attr: str
    weight: float = 1.0
    prefer: Any = None
    direction: Optional[str] = None  # "higher" | "lower"
    lo: Optional[float] = None
    hi: Optional[float] = None

    def score(self, option: dict) -> tuple:
        """Return (contribution, weight)."""
        val = option.get(self.attr, _MISSING)
        if self.prefer is not None:
            return (self.weight if val == self.prefer else 0.0, self.weight)
        if self.direction and val is not _MISSING and self.lo is not None and self.hi is not None:
            span = self.hi - self.lo
            norm = 0.0 if span == 0 else (float(val) - self.lo) / span
            norm = max(0.0, min(1.0, norm))
            if self.direction == "lower":
                norm = 1.0 - norm
            return (self.weight * norm, self.weight)
        return (0.0, self.weight)

    def to_dict(self) -> dict:
        d = {"attr": self.attr, "weight": self.weight}
        if self.prefer is not None:
            d["prefer"] = self.prefer
        if self.direction is not None:
            d.update(direction=self.direction, lo=self.lo, hi=self.hi)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "UtilityTerm":
        return cls(attr=d["attr"], weight=d.get("weight", 1.0), prefer=d.get("prefer"),
                   direction=d.get("direction"), lo=d.get("lo"), hi=d.get("hi"))


@dataclass
class PartySpec:
    """One owner's declarative position: hard red lines + soft utility terms."""
    owner: str
    hard: list = field(default_factory=list)      # list[Constraint]
    utility: list = field(default_factory=list)   # list[UtilityTerm]

    def to_sheet(self) -> PreferenceSheet:
        hard = [HardConstraint(name=c.describe(), predicate=c.check) for c in self.hard]
        terms = self.utility
        if not terms:
            return PreferenceSheet(self.owner, hard=hard, utility=None)

        def _util(option: dict) -> float:
            got = tot = 0.0
            for t in terms:
                c, w = t.score(option)
                got += c
                tot += w
            return got / tot if tot else 0.5

        return PreferenceSheet(self.owner, hard=hard, utility=_util)

    def to_dict(self) -> dict:
        return {"owner": self.owner,
                "hard": [c.to_dict() for c in self.hard],
                "utility": [t.to_dict() for t in self.utility]}

    @classmethod
    def from_dict(cls, d: dict) -> "PartySpec":
        return cls(owner=d["owner"],
                   hard=[Constraint.from_dict(c) for c in d.get("hard", [])],
                   utility=[UtilityTerm.from_dict(t) for t in d.get("utility", [])])


@dataclass
class DecisionSpec:
    """A full recipe: the shared options + every party's declarative position."""
    title: str
    options: list                                  # list[dict]
    parties: list = field(default_factory=list)    # list[PartySpec]

    def to_agents(self) -> list:
        return [Agent(p.owner, p.to_sheet()) for p in self.parties]

    def run(self, rule: str = "egalitarian"):
        return run_consensus(self.to_agents(), self.options, rule=rule)

    def to_dict(self) -> dict:
        return {"title": self.title, "options": self.options,
                "parties": [p.to_dict() for p in self.parties]}

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionSpec":
        options = list(d["options"])
        validate_options(options)
        return cls(title=d["title"], options=options,
                   parties=[PartySpec.from_dict(p) for p in d.get("parties", [])])

    @classmethod
    def from_json(cls, text: str) -> "DecisionSpec":
        import json
        return cls.from_dict(json.loads(text))

    @classmethod
    def load(cls, path: str) -> "DecisionSpec":
        with open(path, encoding="utf-8") as fh:
            return cls.from_json(fh.read())
