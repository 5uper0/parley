# 06 — Negotiation orchestration

## Purpose

Coordinate proposal rounds around the unchanged consensus engine while preserving honest deadlock
and preventing private-feedback leakage.

## Interface

- `start_round(case_id) -> Round`
- `evaluate_round(round_id) -> RoundResult`
- `request_revision(round_id, participant_id) -> RevisionRequest`
- `close_deadlock(case_id, reason="no_feasible_option")`

## Round model

Maximum three rounds. A round locks case version, sheet versions, agenda schema and option set. Each
owner-side evaluator returns a masked verdict. Feasible options are ranked by existing max-min;
only the winning proposal proceeds to ratification.

## Invariants

- Coordinator never receives constraint names, raw answers or private evidence.
- No feasible option produces deadlock, not a relaxed constraint.
- A participant revision creates new sheet and round versions; history remains append-only.
- Repeated probing cannot expose which threshold caused rejection; public feedback is status-only.
- A round never starts until all required sheets are confirmed.

## Acceptance criteria

- Same locked inputs always produce the same decision and transcript hash.
- Stale results cannot overwrite a newer round.
- Three failed rounds close honestly with a usable deadlock receipt.
- Tests cover concurrent revision, retry idempotency, masked feedback and max-round enforcement.

## Not in MVP

Continuous chat bargaining, majority voting, human mediator override, alternative consensus rules.
