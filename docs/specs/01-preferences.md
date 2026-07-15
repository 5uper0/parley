# preferences.py — Spec

## Purpose

`parley/preferences.py` holds an owner's private position and is the origin of the
non-betrayal guarantee. It enforces the **hard/soft split** that is "the heart of Parley":
red lines are code predicates that *reject* an option deterministically, and soft utility
only ranks options that already clear every red line. Because a red line is a boolean
predicate — never negotiable utility — "my agent won't betray me" becomes a provable code
property rather than an LLM's discretion. The `PreferenceSheet` never leaves the owner's
process; only the masked `Evaluation` it produces is consumed downstream.

## Public API

- `@dataclass(frozen=True) class HardConstraint(name: str, predicate: Callable[[Any], bool])`
  — a named red line; `predicate(option) is True` means the option is acceptable to this constraint.
- `@dataclass(frozen=True) class Evaluation(feasible: bool, violated: list, score: float)`
  — the result of scoring one option against the sheet.
- `class PreferenceSheet.__init__(self, owner: str, hard: Optional[list] = None, utility: Optional[Callable[[Any], float]] = None)`
  — build a sheet for `owner` with red lines `hard` and an optional soft utility function.
- `PreferenceSheet.evaluate(self, option: Any) -> Evaluation`
  — check `option` against every red line and compute its clamped soft score.

## Data model

`HardConstraint` (frozen):
- `name: str` — human label for the red line (stays private to the owner).
- `predicate: Callable[[Any], bool]` — returns `True` when the option satisfies this constraint.

`Evaluation` (frozen):
- `feasible: bool` — `True` iff **all** hard constraints pass.
- `violated: list` — names of the crossed red lines; private to the owner, not masked at this layer.
- `score: float` — soft utility in `[0, 1]`.

`PreferenceSheet` (plain class, not a dataclass; mutable attributes):
- `owner: str` — the principal this sheet represents.
- `hard: list` — `list(hard) if hard else []` (copied defensively; empty list, never `None`).
- `utility: Optional[Callable[[Any], float]]` — soft ranking function, or `None`.

## Invariants (must never break)

- **Hard constraints are veto, not utility.** `feasible` is `not violated` — a single failed
  predicate makes the option infeasible regardless of soft `score`. The two axes are computed
  independently in `evaluate`; a red line can never be "bought out" by high utility. Collapsing
  red lines into utility would destroy non-betrayal.
- **Score is clamped to `[0, 1]`.** `evaluate` applies `max(0.0, min(1.0, float(self.utility(option))))`.
  A user-supplied utility returning out-of-range or non-float-ish values is forced into range,
  keeping the downstream max-min comparison in `consensus.py` well-defined.
- **Absent utility is neutral, not zero.** With `utility is None` the score is `0.5`, so an owner
  who expressed no soft preference neither drags the Rawlsian floor down nor games it up. Feasibility
  is unaffected.
- **`violated` carries real names, and stays here.** This layer *does* name which constraints failed
  (the owner needs that locally). The masking to `"ok"`/`"red-line"` happens one layer up in
  `agent.py` — a `PreferenceSheet`/`Evaluation` must never be handed to the coordinator directly.

## Interactions

- **Called by** `agent.py` (`Agent.consider` → `self.sheet.evaluate(option)`, which maps `feasible`
  → `acceptable`, passes `score` through, and drops `violated` in favor of a masked reason), and by
  `transcript.py` (`Transcript.verify_non_betrayal` → `sheet.evaluate(decision).feasible`) when an
  owner replays their own sheet against the final decision.
- **Calls** nothing outside stdlib; depends only on `dataclasses` and `typing`. Zero-dependency.
- **Data crossing the boundary:** in — an arbitrary `option` (in examples/tests a dict like
  `{"day": ..., "hour": ...}`). Out — an `Evaluation`, consumed only inside the owner's trust
  boundary. The sheet itself is never handed to the coordinator.

## Failure modes / edge cases

- **No hard constraints** (`hard=[]` or `None`) → `violated == []` → always `feasible=True`.
- **No utility** (`utility=None`) → `score == 0.5`.
- **Utility returns out-of-range / non-numeric** → clamped via `float(...)` then `[0,1]`; a utility
  returning something `float()` cannot coerce raises `TypeError`/`ValueError` (unhandled — trusted
  input inside the owner's own process).
- **Predicate raises** on a malformed option → the exception propagates (predicates are the owner's
  own trusted code, assumed total over the option space; no defensive catch).
- **Multiple violations** → all failing names are collected in `violated` (order follows `self.hard`).

## Test coverage

`tests/test_preferences.py`:
- `test_feasible_when_all_hard_constraints_pass` — a slot passing `no-mornings` gives
  `feasible is True`, `violated == []`, `score == 1.0`.
- `test_infeasible_lists_violated_constraint_names` — a Friday morning trips both `no-mornings`
  and `no-friday`; `feasible is False` and `set(violated) == {"no-mornings", "no-friday"}`.
- `test_utility_defaults_to_neutral_when_absent` — a sheet with `hard=[]` and no utility yields
  `feasible True` and `0.0 <= score <= 1.0` (the neutral `0.5`).

## Open questions / roadmap

Per `docs/ROADMAP.md` (Exp 1), `PreferenceSheet` is currently constructed in code. The next
step is `parley/elicit.py`: an LLM turns a natural-language position into a `PreferenceSheet`
(hard vs soft constraints), with `tests/test_elicit.py`. That must keep this deterministic core
intact — the LLM produces the sheet, code still enforces it. The sheet's shape (named
`HardConstraint` predicates + a `[0,1]` utility) is the target elicitation must produce, so this
module is expected to stay stable while the *source* of sheets changes. Weighted / non-uniform
constraint semantics are out of scope by design: a red line is strictly binary (pass/fail).
