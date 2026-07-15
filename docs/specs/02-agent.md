# agent.py — Spec

## Purpose

`parley/agent.py` is the **masking boundary**. An `Agent` faithfully represents one owner,
but the only thing that ever leaves it is a `Verdict`: `acceptable` + a soft `score` + a
*masked* `reason` (`"ok"` or `"red-line"`). It never names which red line was crossed and
never exposes the `PreferenceSheet`. This is what makes the coordinator "untrusted by
construction": non-betrayal is code-enforced here, not left to an LLM's discretion. Masking
the reason is what keeps rival owners' private positions private even as they negotiate.

## Public API

- `@dataclass(frozen=True) class Verdict(owner: str, acceptable: bool, score: float, reason: str, sig: Optional[str] = None, pubkey_hex: Optional[str] = None)`
  — the single public artifact an agent emits for one option; `reason` is already masked.
- `class Agent.__init__(self, owner: str, sheet: PreferenceSheet)`
  — bind a delegate to its owner and that owner's private sheet.
- `Agent.consider(self, option: Any) -> Verdict`
  — evaluate `option` against the private sheet and return a masked `Verdict`.

## Data model

`Verdict` (frozen dataclass — the wire/transcript unit):
- `owner: str` — which principal this verdict speaks for.
- `acceptable: bool` — mirrors `Evaluation.feasible`; all the owner's red lines held.
- `score: float` — the owner's soft utility in `[0, 1]` for this option.
- `reason: str` — masked: `"ok"` when acceptable, `"red-line"` when not. Never names the constraint.
- `sig: Optional[str] = None` — optional Ed25519 signature over `(option, verdict)`; `None` for
  local agents. Plain string so the zero-dependency core never imports the crypto lib.
- `pubkey_hex: Optional[str] = None` — optional signer public key (hex); `None` for local agents.

`Agent` (plain class):
- `owner: str` — the represented principal.
- `sheet: PreferenceSheet` — **private**; never handed to the coordinator.

## Invariants (must never break)

- **`reason` is masked, always.** It is exactly `"ok" if ev.feasible else "red-line"`. It must
  never carry `Evaluation.violated`, the constraint name, or any per-constraint detail. Leaking
  which red line was hit would betray the owner's private position.
- **The sheet never escapes.** `consider` returns a `Verdict` and nothing that references the
  sheet; `Verdict` has no field for constraints or utility. The frozen dataclass has no `sheet`,
  `hard`, or `violated` attribute — verified by test.
- **Faithful mapping.** `acceptable == ev.feasible` and `score == ev.score`; the agent does not
  re-rank, soften, or override its owner's evaluation. It is a pure pass-through of the masked
  fields.
- **Signatures are opaque to the core.** `sig`/`pubkey_hex` are plain `Optional[str]`; the local
  `Agent` leaves them `None`. Crypto is populated only by the networked/signed bots (`net/`) so the
  core imports no crypto library.

## Interactions

- **Calls** `PreferenceSheet.evaluate(option)` (from `preferences.py`) — the only computation it does.
- **Called by** `consensus.run_consensus`, which invokes `a.consider(option)` for each agent. The
  networked path (`net/client.RemoteAgent`) implements the identical `.owner` / `.consider()`
  interface, so `run_consensus` cannot tell local from remote.
- **Produces** `Verdict`s that `transcript.Transcript.record` logs (copying `owner`, `acceptable`,
  `score`, `reason`, `sig`, `pubkey_hex`).
- **Data crossing the boundary:** in — an arbitrary `option`. Out — a `Verdict` with a masked
  reason. The private `Evaluation.violated` is discarded here and never crosses the boundary.

## Failure modes / edge cases

- **Infeasible option** → `acceptable=False`, `reason="red-line"`, but a real `score` is still
  reported (the score is computed regardless of feasibility; consensus ignores scores of
  infeasible options).
- **Multiple red lines crossed** → still a single `"red-line"` (the count and identities are not
  observable from the verdict).
- **Predicate/utility raises** inside `evaluate` → propagates out of `consider` (owner's own trusted
  code; no defensive handling in this module).
- **No signature** → `sig`/`pubkey_hex` stay `None`; downstream signature verification is
  skipped for local agents.

## Test coverage

`tests/test_agent.py`:
- `test_verdict_accepts_feasible_option` — feasible slot → `owner == "ana"`, `acceptable is True`,
  `reason == "ok"`, `score == 1.0`.
- `test_verdict_rejects_on_red_line_with_masked_reason` — morning slot → `acceptable is False`,
  `reason == "red-line"` (explicitly asserts it does NOT say which red line).
- `test_verdict_never_leaks_the_sheet_or_which_constraint` — `repr(v)` + `v.__dict__` contains no
  `"no-mornings"`; the verdict has no `hard` key and no `sheet` attribute.

## Open questions / roadmap

The masking contract is intentionally minimal and stable. Signed verdicts (Ed25519 over
`(option, verdict)`) already exist behind the `sig`/`pubkey_hex` fields and are populated by the
`net/` bots — see CLAUDE.md ("Signed verdicts"). Roadmap Exp 1 adds multi-round
counter-proposals in `consensus.py`; if agents begin proposing (not just scoring), the masking
guarantee on `reason` still governs what a counter-proposal may reveal. No changes to `Verdict`'s
masked-reason contract are planned.
