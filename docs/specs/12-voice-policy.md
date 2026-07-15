# voice/policy.py — Spec

## Purpose
This module is the speech-side of non-betrayal: **what the voice agent is ALLOWED to say**. The
consensus core already masks *why* an option is rejected (`Verdict.reason == "red-line"`, never the
constraint name), but voice reopens that leak — a chatty LLM asked to sound natural will volunteer
"I can't do Friday because my owner…". So the agent never generates its own commitments in words; it
may only speak lines drawn from here, and the **code** (not the LLM) picks which one from a
code-produced `Evaluation`. Three outcomes, nothing else leaves the agent's mouth: accept, masked
refuse, fail-closed clarify. This keeps a spoken commitment provably downstream of `sheet.evaluate`.

## Public API

- `ACCEPT = "That works for me — I accept."` — a commitment; only ever reached through the sheet,
  never persuasion.
- `REFUSE = "That isn't acceptable to me. Please propose a different option."` — masked: no reason,
  no constraint, no attribute, no score.
- `CLARIFY = "I didn't catch a concrete proposal — could you state it precisely?"` — fail-closed:
  the proposal couldn't be pinned to a concrete option.
- `reply_for(ev: Evaluation | None) -> str`
  — map a code-produced `Evaluation` to a masked, speakable line. `None` means "nothing to evaluate"
  → `CLARIFY`. Otherwise `ACCEPT` if `ev.feasible` else `REFUSE`.

## Data model
- **Whitelisted lines** — three module-level string constants. Deliberately reason-free and
  interchangeable: none names a constraint, an attribute, or a score, so swapping which one is spoken
  reveals nothing. The *code* selects; the LLM never authors a commitment line.
- **`Evaluation`** (from `parley/preferences.py`, frozen): `feasible: bool`, `violated: list`,
  `score: float`. `reply_for` reads **only `feasible`** — `violated` and `score` are ignored, so they
  cannot leak through the spoken line.

## Invariants (must never break)
- **Refusals are masked.** `REFUSE` is a fixed string with no constraint/attribute/threshold/score.
  `reply_for` branches solely on `ev.feasible` and never interpolates `ev.violated` or `ev.score`.
- **Accept is downstream of the sheet.** `ACCEPT` is returned only when `ev.feasible` is true, and
  `ev` is always the output of `sheet.evaluate` in the caller — there is no path from persuasion or
  the LLM's own judgement to `ACCEPT`.
- **Fail-closed on `None`.** A missing/unpinnable option (`ev is None`) yields `CLARIFY`, never
  `ACCEPT`. The absence of a decision is treated as "ask again", never as agreement.
- **Exactly three outcomes.** `reply_for` is total over `{None} ∪ Evaluation` and returns one of the
  three whitelisted constants — no other string can leave via this function.

## Interactions
- **Called by `voice/gateway.py`:** `_Gateway.decide_reply` (deterministic path) computes
  `ev = self.sheet.evaluate(option)` when `extract_option` pinned an option, else `ev = None`, then
  returns `reply_for(ev)`. The result is streamed as the SSE reply.
- **`voice/brain.py`** reuses the *exact same strings* verbatim in the model's system prompt / expected
  outputs (e.g. the accept and refuse lines match `ACCEPT`/`REFUSE`), keeping the deterministic and
  conversational paths' spoken vocabulary identical — but `brain.py` imports the constants indirectly
  by matching text, not by importing this module.
- **parley core:** consumes `Evaluation` from `parley/preferences.py`; produces nothing back to the
  core. Data crossing the boundary is only the chosen constant string.

## Failure modes / edge cases
- **`ev is None` (unparsed / no option):** `CLARIFY`. This is the fail-closed default — the gateway's
  `extract_option` returning `None` routes here.
- **`ev.feasible is False` (red line crossed):** `REFUSE`, with `ev.violated` deliberately unread.
- **`ev.feasible is True`:** `ACCEPT`.
- No exceptions are raised or caught here; the function is a pure total map. Malformed input can only
  arrive as a non-`Evaluation`, which is out of the caller's contract (the gateway always passes an
  `Evaluation` or `None`).

## Test coverage
No dedicated `tests/test_voice_policy.py`; the constants and `reply_for`'s selection are exercised
end-to-end through the gateway and brain:
- `tests/test_voice_gateway.py` imports `ACCEPT, REFUSE, CLARIFY` and asserts the SSE reply equals the
  right constant for feasible (`ACCEPT`), red-line (`REFUSE`, plus a leak check that `"heir2"`, `"30"`,
  `"red"` are absent), `key=value` (`ACCEPT`), and unparsable (`CLARIFY`) turns.
- `tests/test_voice_brain.py` asserts the brain's spoken replies equal the same accept/refuse strings
  after the masked `consider_option` result.

## Open questions / roadmap
- **Line variety.** A single fixed line per outcome is intentional (interchangeable, reason-free); if
  natural-sounding variety is wanted, any expansion must keep every variant reason-free and
  code-selected — the invariant, not the wording, is load-bearing.
- **Localization.** Lines are English literals; a multilingual voice agent would need per-locale
  whitelists that preserve the no-reason/no-attribute property.
- Policy is an **optional voice-layer leaf** with no ROADMAP experiment of its own; it exists purely to
  stop the speech path from re-opening the leak the core already closes.
