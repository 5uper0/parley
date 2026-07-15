# 03 — Private elicitation

## Purpose

Turn a participant's ordinary-language account into a private declarative position without letting
an LLM silently decide what the participant meant.

## Flow

1. Ask separately for desired outcome, unacceptable outcomes, acceptable costs, priorities, private
   information, and fallback.
2. Produce a draft with `shared_claims`, `hard_constraints`, `utility_terms`, and uncertainties.
3. Show the participant a plain-language review: “must never”, “prefer”, and “not understood”.
4. Require explicit confirmation for every hard constraint and the complete sheet version.

## Interface

- `start_interview(case_id, participant_id) -> Interview`
- `answer(interview_id, prompt_id, text) -> Interview`
- `draft_sheet(interview_id) -> SheetDraft`
- `confirm_sheet(draft_id, confirmations) -> ConfirmedSheet`
- `revise_sheet(sheet_id, changes) -> SheetDraft`

## Invariants

- Raw answers and sheets never enter prompts shared with another participant.
- LLM extraction cannot create executable predicates; output must validate against the declarative
  `Constraint`/`UtilityTerm` schema.
- Ambiguity fails to an owner-visible question, never an inferred red line.
- Only the participant can confirm or revise their sheet.
- Confirmation records the exact structured version and human-readable rendering.

## Acceptance criteria

- User can correct, remove and reclassify every extracted item.
- Missing required meaning produces `needs_clarification`, not a guessed value.
- Prompt-injection text inside an answer cannot access other sheets or alter system policy.
- Tests cover red-line confirmation, soft preference weighting, ambiguity and schema rejection.

## Not in MVP

Autonomous legal analysis, voice elicitation, sentiment-based constraints, hidden personalization.
