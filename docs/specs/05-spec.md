# parley/spec.py — Spec

## Purpose
`DecisionSpec` expresses a whole parley — the shared options plus every party's red lines
and preferences — as **plain data, never executable Python**. That makes a recipe shareable
and importable as JSON, so a gallery/UI can ship recipes without shipping a backdoor (no
code executes on load). The module then *compiles* that declarative form into the existing
engine (`PreferenceSheet` → `Agent` → `run_consensus`) which stays untouched. It is the safe,
serializable front door to the same deterministic non-betrayal core. Zero-dependency: stdlib
only.

## Public API

- `@dataclass(frozen=True) Constraint(attr: str, op: str, value: Any)`
  — a red line as data: `option[attr] <op> value` must hold.
  - `.check(option: dict) -> bool` — evaluate the predicate; missing attr → `False`
    (fails closed); unknown `op` → `ValueError`.
  - `.describe() -> str` — `"{attr} {op} {value!r}"`, used as the (private) constraint name.
  - `.to_dict()` / `.from_dict(d)` — JSON round-trip.
- `@dataclass(frozen=True) UtilityTerm(attr, weight=1.0, prefer=None, direction=None, lo=None, hi=None)`
  — one soft term, categorical (`prefer` a value) or numeric (`direction` `"higher"`/`"lower"`
    normalized on `[lo, hi]`).
  - `.score(option: dict) -> tuple` — `(contribution, weight)`.
  - `.to_dict()` / `.from_dict(d)`.
- `@dataclass PartySpec(owner: str, hard: list = [], utility: list = [])`
  — one owner's declarative position (`list[Constraint]` + `list[UtilityTerm]`).
  - `.to_sheet() -> PreferenceSheet` — compile to a real sheet.
  - `.to_dict()` / `.from_dict(d)`.
- `@dataclass DecisionSpec(title: str, options: list, parties: list = [])`
  - `.to_agents() -> list[Agent]` — one `Agent(owner, sheet)` per party.
  - `.run(rule: str = "egalitarian")` — build agents and call `run_consensus(agents, options, rule=rule)`.
  - `.to_dict()` / `.from_dict(d)` / `.from_json(text)` / `.load(path)` — serialize / load.

## Data model

- **`Constraint`** (frozen): `attr`, `op` (one of `== != < <= > >= in not_in`), `value`.
- **`UtilityTerm`** (frozen): `attr`, `weight` (default `1.0`), plus either `prefer` (categorical
  target) or the numeric triple `direction` + `lo` + `hi`.
- **`PartySpec`**: `owner`, `hard: list[Constraint]`, `utility: list[UtilityTerm]`.
- **`DecisionSpec`**: `title`, `options: list[dict]` (the shared public options), `parties: list[PartySpec]`.
- **`_MISSING`** sentinel — distinguishes "attribute absent" from a stored `None`/falsy value,
  in both `Constraint.check` and `UtilityTerm.score`.

## Invariants (must never break)

- **Recipes are data, not code.** Every field is JSON-native; `from_json`/`load` do
  `json.loads` + `from_dict`, never `eval`/`exec`/import of caller code. A gallery loading a
  shared recipe can therefore not be made to execute arbitrary Python — the whole reason the
  module exists.
- **The compiled sheet enforces the same hard/soft split.** `PartySpec.to_sheet` maps each
  `Constraint` to a `HardConstraint(name=c.describe(), predicate=c.check)` and folds the
  `UtilityTerm`s into a single utility function — so red lines remain vetoes in
  `preferences.py`, never traded against utility. spec.py adds a serialization layer; it does
  **not** relax the guarantee.
- **Missing attributes fail closed.** `Constraint.check` returns `False` when `attr` is
  absent, so a red line over an attribute an option doesn't carry is treated as *not
  satisfied* (the option is rejected), never silently passed. (`test_constraint_missing_attr_fails_closed`.)
- **Constraint names stay private.** `describe()` becomes the `HardConstraint.name`, which
  `preferences.py`/`agent.py` keep in the owner's `Evaluation.violated` and mask before
  anything leaves the process. The descriptive name is convenience, not something emitted
  publicly.
- **Utility contribution is bounded and averaged.** `to_sheet` computes
  `got / tot` (weighted average, falling back to neutral `0.5` when total weight is 0), and
  each numeric `UtilityTerm.score` clamps its normalized value to `[0, 1]` — so a recipe
  cannot inject an out-of-range score that would distort the max-min comparison.

## Interactions

- **`preferences.py`**: `to_sheet` constructs `HardConstraint` and `PreferenceSheet`
  directly.
- **`agent.py`**: `to_agents` wraps each sheet in `Agent(owner, sheet)`.
- **`consensus.py`**: `run` delegates to `run_consensus(agents, options, rule=rule)` and
  returns its result (carrying `.status`, `.decision`, `.transcript`).
- **`transcript.py`**: the returned result exposes the `Transcript`; owners can call
  `verify_non_betrayal(party.to_sheet(), result.decision)` — compiling the party twice yields
  an equivalent sheet (`test_non_betrayal_holds_on_decision`).
- **Data crossing the boundary**: only JSON-native structures (dicts/lists/scalars). The
  compiled predicates/utility closures live in-process and are never serialized.

## Failure modes / edge cases

- **Unknown operator**: `Constraint.check` raises `ValueError(f"unknown operator: {op!r}")`.
  This is the one hard failure — an invalid recipe surfaces loudly rather than silently
  mis-evaluating.
- **Missing constrained attribute**: fails closed → option rejected (see invariant).
- **`UtilityTerm` with neither `prefer` nor a complete numeric triple**: `score` returns
  `(0.0, weight)` — a neutral, non-crashing contribution.
- **Numeric term with `lo == hi`** (`span == 0`): `norm` set to `0.0` rather than dividing by
  zero.
- **Party with no utility terms**: `to_sheet` builds the sheet with `utility=None`
  (neutral 0.5 downstream), not an empty-average error.
- **No feasible option for everyone**: `run` propagates a `"deadlock"` status from consensus
  (`test_deadlock_when_nothing_feasible`).
- **Malformed JSON / missing required keys** (`title`, `options`, `attr`, `op`, `value`,
  `owner`): raises the standard `json`/`KeyError` from `from_dict`; there is no bespoke schema
  validation layer.

## Test coverage

`tests/test_spec.py`:
- `test_constraint_ops` — every operator (`<=`, `==`, `!=`, `in`, `not_in`) evaluates correctly.
- `test_constraint_missing_attr_fails_closed` — absent attr → `check` returns `False`.
- `test_utility_categorical_and_numeric` — categorical full/zero weight; numeric lower-is-better
  endpoints (`1.0` at lo, `0.0` at hi).
- `test_party_to_sheet_feasible_and_score` — compiled sheet: feasible option scores `1.0`;
  red-line violation → `feasible is False` with `violated` populated (privately).
- `test_run_picks_max_min_and_blocks_red_line` — a full KYC recipe: egalitarian middle option
  wins; the tempting high-revenue option is recorded infeasible for someone.
- `test_deadlock_when_nothing_feasible` — no feasible option → `status == "deadlock"`.
- `test_non_betrayal_holds_on_decision` — each party replays its recompiled sheet → non-betrayal
  holds.
- `test_json_round_trip` — `to_dict`/`from_dict` preserves the recipe and its decision.

## Open questions / roadmap
- **NL → spec (Exp 1).** `docs/ROADMAP.md` plans `parley/elicit.py` to turn a natural-language
  position into sheets; `DecisionSpec` is the natural declarative target for elicited output,
  but that path isn't built yet.
- **Schema validation.** No JSON-schema/version field guards a loaded recipe; malformed input
  raises raw `KeyError`/`ValueError`. A gallery would likely want explicit validation + a
  `protocol`/version tag.
- **Multi-round counter-proposals.** ROADMAP anticipates consensus over *generated* options,
  not only a fixed `options` list; `DecisionSpec.options` is static today.
