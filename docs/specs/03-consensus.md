# consensus.py — Spec

## Purpose

`parley/consensus.py` reaches a decision among delegates with **conflicting private
interests** while seeing only masked verdicts — never the sheets. It enforces two
non-betrayal guarantees: a decision is valid only if it is **feasible for every agent**
(all red lines pass), and among those feasible options it applies the **Rawlsian max-min**
rule — lift the least-happy participant, tie-broken by total welfare — rather than a
majority vote. When no option is feasible for all, it returns an **honest deadlock** rather
than forcing a bad decision on someone.

## Public API

- `@dataclass class ConsensusResult(status: str, decision: Optional[Any], transcript: Transcript)`
  — the outcome: `status` is `"agreed"` or `"deadlock"`, `decision` is the chosen option (or `None`),
  `transcript` is the tamper-evident record.
- `def run_consensus(agents, options, rule: str = "egalitarian") -> ConsensusResult`
  — score every option with every agent, record the verdicts, and pick the max-min winner among
  options feasible for all (or deadlock).

## Data model

`ConsensusResult` (mutable dataclass):
- `status: str` — `"agreed"` | `"deadlock"`.
- `decision: Optional[Any]` — the winning option, or `None` on deadlock.
- `transcript: Transcript` — the finalized record (see `transcript.py`).

Internal working structure inside `run_consensus`:
- `feasible: list[tuple[option, floor_score, total_score]]` — one tuple per option acceptable to
  **every** agent, where `floor = min(v.score ...)` and `total = sum(v.score ...)`.

## Invariants (must never break)

- **Feasibility is unanimous and gating.** An option enters `feasible` only if
  `all(v.acceptable for v in verdicts)`. A single `red-line` verdict excludes the option, no matter
  how high everyone else's score is. This is where "no forced bad decision" lives.
- **Egalitarian ordering: floor first, then total.** The winner is
  `max(feasible, key=lambda x: (x[1], x[2]))` — highest Rawlsian floor, tie-broken by highest total
  welfare. Never majority vote, never plain sum. Weakening the floor priority breaks the
  least-happy-first guarantee.
- **Deterministic tie-break.** `max` over the `(floor, total)` key is stable across the input order,
  so the same `options` list yields the same decision (reproducibility for the transcript hash).
- **The coordinator sees only verdicts.** `run_consensus` only ever reads `v.acceptable` and
  `v.score` and records masked verdicts; it never touches a `PreferenceSheet`. The transcript
  therefore never contains constraint names.
- **Honest deadlock.** Empty `feasible` ⇒ `finalize(status="deadlock", decision=None)` and
  `ConsensusResult("deadlock", None, transcript)`. No fallback to a "best infeasible" option.

## Interactions

- **Calls** `agent.consider(option)` for each agent (works identically for local `Agent` and remote
  `RemoteAgent` — the seam is deliberate) and `Transcript.record` / `Transcript.finalize` from
  `transcript.py`.
- **Called by** the examples (`examples/meeting.py`, `examples/run_env.py`) and by owners' end-to-end
  flows; the caller then uses `result.transcript` and `verify_non_betrayal` to prove non-betrayal.
- **Data crossing the boundary:** in — a list of agents and a list of `options`, plus `rule`. Out —
  a `ConsensusResult`; every masked verdict is captured in `result.transcript` (SHA-256-hashable).

## Failure modes / edge cases

- **No feasible option for all** → `status == "deadlock"`, `decision is None`; transcript still holds
  every option's verdicts.
- **Ties on the floor score** → resolved by higher `total`; if still tied, `max` keeps the first
  encountered (input-order stable).
- **Unknown rule** → `run_consensus(..., rule="something")` raises `ValueError(f"unknown rule: {rule!r}")`.
  Note: the rule check happens **after** the feasibility scan, so an unknown rule on a fully-deadlocked
  input returns a deadlock result *without* raising (the `if not feasible` branch returns first).
- **Empty `options`** → `feasible` stays empty → deadlock.
- **Empty `agents`** → `all(...)` over an empty verdict list is vacuously `True`, so every option is
  feasible with `floor`/`total` over an empty sequence; `min([])`/`sum([])` — `sum` is `0`, but
  `min` on empty raises `ValueError`. In practice consensus is always run with ≥1 agent; empty-agent
  input is not a supported case.

## Test coverage

`tests/test_consensus.py` (ana bans mornings, bob bans Friday):
- `test_reaches_consensus_feasible_for_all` — `status == "agreed"`, decision is one of
  `{mon-15, tue-12}`, and the decision satisfies every red line (`hour >= 12` and `day != "fri"`).
- `test_egalitarian_rule_maximises_the_least_happy` — tue-12 (floor 0.6) beats mon-15 (floor 0.5),
  so `decision == slot("tue", 12)` — proves floor-first ordering.
- `test_honest_deadlock_when_no_option_is_feasible_for_all` — adding cara (demands Friday) against
  ana (no mornings) and bob (no Friday) → `status == "deadlock"`, `decision is None`.
- `test_coordinator_only_sees_verdicts_not_sheets` — `str(r.transcript.to_dict())` contains neither
  `"no-mornings"` nor `"no-friday"`.

## Open questions / roadmap

Per `docs/ROADMAP.md` (Exp 1) and CLAUDE.md, `run_consensus` today only *scores a fixed set of
options*. The next step is **multi-round counter-proposals** — agents propose new options rather
than only ranking given ones. Exp 4 ("Moat") plans an adversarial test of **manipulating the
max-min rule** (collusion-resistance), to be deepened only once a paying segment is plausible. The
`rule` parameter is a forward hook: `"egalitarian"` is the only implemented social-choice rule and
any other value raises.
