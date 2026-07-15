# 05 — Proposal generation

## Purpose

Generate a small, bounded set of concrete agreement options from shared facts and confirmed sheets,
then hand plain data to the deterministic engine. The generator proposes; it never decides.

## Interface

- `build_agenda(case_version, sheet_capabilities) -> AgendaSchema`
- `generate_options(agenda, shared_facts, masked_feedback, round) -> list[OptionDraft]`
- `validate_option(schema, option) -> ValidatedOption`

## Rules

- Generate 3–7 materially different options per round, including the status quo/fallback when safe.
- Every option uses only attributes declared in a versioned agenda schema.
- Amounts, dates and obligations are explicit; no option contains vague commitments such as
  “reasonable payment”.
- The generator sees shared facts and masked feasibility feedback, not private sheets or violated
  constraint names.
- Duplicate and dominated options are removed before scoring.

## Invariants

- No generated text or code executes.
- Schema-invalid, missing-attribute and out-of-domain options never reach consensus.
- The generator cannot mark an option feasible, selected or agreed.
- Shared legal uncertainty is rendered as uncertainty, not resolved by the model.

## Acceptance criteria

- Reference lease case produces the agreed notice/replacement/deposit alternative.
- Prompt injection in shared facts cannot expand schema or request private data.
- Deterministic fixtures validate numeric bounds, dates, duplicates and missing attributes.

## Not in MVP

Open-ended contract drafting, web research, legal recommendations, unlimited option search.
