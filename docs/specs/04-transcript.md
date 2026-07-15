# parley/transcript.py — Spec

## Purpose
The `Transcript` is Parley's **tamper-evident, verifiable record** of a parley. It holds
only *public* verdicts (never sheets), so publishing it leaks no private position. `hash()`
is a deterministic SHA-256 over the canonical record, making any post-hoc edit detectable.
`verify_non_betrayal` lets each owner **replay their OWN private sheet** against the final
decision locally — proving no red line was crossed without revealing the sheet to anyone.
This is the module that turns "my agent wasn't betrayed" from a hope into a property each
owner can check for themselves.

## Public API

- `class Transcript.__init__(self)` — empty record: `entries = []`, `result = None`.
- `Transcript.record(self, option: Any, verdicts) -> None`
  — append one option and its list of masked `Verdict`s to the log (see Data model for the
  fields kept per verdict).
- `Transcript.finalize(self, status: str, decision: Any) -> None`
  — set the outcome: `result = {"status": status, "decision": decision}`.
- `Transcript.to_dict(self) -> dict`
  — the canonical dict: `{"entries": [...], "result": {...}|None}`.
- `Transcript.hash(self) -> str`
  — SHA-256 hex digest of `json.dumps(to_dict(), sort_keys=True, ensure_ascii=False, default=str)`.
- `Transcript.verify_non_betrayal(self, sheet: PreferenceSheet, decision: Any) -> bool`
  — replay one owner's private sheet against the decision; `True` iff every red line held
  (or the decision is `None`).

## Data model

- **`entries`**: `list[dict]`, one per option recorded, each
  `{"option": <Any>, "verdicts": [<verdict-dict>, ...]}`.
- **verdict-dict** (per recorded `Verdict`, exactly six masked/public fields):
  `owner`, `acceptable`, `score`, `reason`, `sig`, `pubkey_hex`. Copied from
  `Verdict.owner/acceptable/score/reason/sig/pubkey_hex`. `reason` is already the *masked*
  `"ok"`/`"red-line"` string produced by `agent.py`; `sig`/`pubkey_hex` are `None` for local
  agents and populated for signed remote bots.
- **`result`**: `Optional[dict]` — `None` until `finalize`, then
  `{"status": <"agreed"|"deadlock"|...>, "decision": <option|None>}`.

## Invariants (must never break)

- **Only public/masked data is ever stored.** `record` copies exactly the six public verdict
  fields; it never stores the `PreferenceSheet`, the `violated` constraint names, or any
  hint of *which* red line was crossed. If a private field ever leaked into an entry, the
  masking guarantee (and `test_wire_never_carries_the_private_sheet`) would break.
- **The hash is canonical and total-order stable.** `sort_keys=True` + `ensure_ascii=False`
  + `default=str` make the digest deterministic across runs/processes, so two honest
  assemblies of the same parley hash-equal and *any* edit flips the hash. Removing any of
  those json flags would make the hash non-reproducible and defeat tamper-evidence.
- **Non-betrayal is checked against the owner's own sheet, not the transcript's claims.**
  `verify_non_betrayal` re-evaluates `sheet.evaluate(decision).feasible` — it does **not**
  trust the recorded verdicts. This is what makes it a proof: an owner needs nothing but
  their private sheet and the public decision.
- **A `None` decision (deadlock) betrays no one.** `verify_non_betrayal(sheet, None)` returns
  `True` unconditionally: an honest deadlock forces nothing on anyone, so no red line can be
  crossed.

## Interactions

- **`consensus.py`** builds and owns the `Transcript`: `run_consensus` calls `record()` per
  option and `finalize()` with the outcome; the result object exposes `.transcript`.
- **`agent.py` / `preferences.py`**: the `Verdict`s handed to `record()` come from
  `Agent.consider()`, which masks `PreferenceSheet.evaluate()`. `verify_non_betrayal`
  delegates straight to `PreferenceSheet.evaluate(decision).feasible`.
- **`net/identity.py`**: reads `entries` in `verify_transcript(transcript)` to re-check every
  signed verdict against its `pubkey_hex` for its own `option`. The `sig`/`pubkey_hex` fields
  carried here are exactly what that check consumes.
- **Data crossing the boundary**: outward, only `to_dict()`/`hash()` (public). Inward,
  `verify_non_betrayal` takes the owner's private sheet but keeps it in the owner's process.

## Failure modes / edge cases

- **Tampering with any stored field** changes `hash()` — `test_tampering_changes_the_hash`
  flips one `acceptable` bool and asserts the digest differs.
- **Non-JSON-native option/decision values** (e.g. custom objects): `default=str` stringifies
  them for hashing rather than raising, so `hash()` never crashes on exotic options.
- **`decision is None`**: `verify_non_betrayal` short-circuits to `True` before touching the
  sheet.
- **A decision that violates a red line**: `verify_non_betrayal` returns `False`
  (`test_non_betrayal_would_fail_if_decision_violated_a_red_line` replays ana's sheet against
  a Friday-morning slot).
- **No integrity error handling by design**: `Transcript` does not itself detect tampering —
  it makes tampering *detectable* by an external `hash()`/`verify_transcript` comparison. It
  never signs, and trusts the caller to store/compare the hash out of band.

## Test coverage

`tests/test_transcript.py`:
- `test_hash_is_deterministic` — two independent `run_consensus` runs produce equal `hash()`.
- `test_tampering_changes_the_hash` — flipping a recorded `acceptable` changes the hash.
- `test_owner_can_prove_non_betrayal_locally` — ana replays her sheet against the agreed
  decision → `True`.
- `test_non_betrayal_would_fail_if_decision_violated_a_red_line` — replaying against a
  red-line-violating slot → `False`.

Also exercised indirectly by `tests/test_net.py`
(`test_wire_never_carries_the_private_sheet` asserts no private constraint name appears in
`to_dict()`; `test_signed_transcript_detects_coordinator_forgery` builds on the recorded
`sig`/`pubkey_hex`) and by `tests/test_spec.py` (`test_non_betrayal_holds_on_decision`).

## Open questions / roadmap
- **Range-masked scores.** `score` is still a plain float in each entry; `docs/ROADMAP.md`
  anticipates masking soft scores (MPC) so even the score isn't in the clear.
- **Bundled hash/signature convenience.** Today integrity relies on the caller comparing
  `hash()` out of band and calling `verify_transcript()` separately; there is no single
  "verify this whole record" entry point that combines hash-anchoring + signatures.
- **Persisted/serialized format.** `to_dict()` exists but there is no `from_dict`/on-disk
  transcript format yet; replay/audit is in-process only.
