# 01 — Case lifecycle

## Purpose

Own the shared case, its participants, public agenda, and legal state transitions. It stores no
private preference content.

## Interface

- `create_case(title, situation, initiator) -> Case`
- `add_participant(case_id, display_name, email) -> Participant`
- `set_shared_facts(case_id, version, facts) -> CaseVersion`
- `transition(case_id, expected_version, event) -> Case`
- `get_case(case_id, viewer) -> CaseView`

## State model

`draft → inviting → eliciting → ready → proposing → ratifying → agreed|deadlocked|expired|cancelled`.
Transitions are append-only events and require optimistic version matching. Terminal cases are
immutable except for export and deletion metadata.

## Invariants

- Case views expose shared facts and progress, never another participant's sheet or elicitation.
- At least two distinct participants are required before `ready`.
- Only confirmed sheets can move a case to `ready`.
- Cancellation cannot convert a proposal into an agreement.
- Every state change records actor, timestamp, prior version and event type.

## Acceptance criteria

- Invalid or stale transitions fail without changing state.
- A participant sees names and completion states, not private answers.
- Terminal state cannot return to negotiation.
- Tests cover the complete transition table, concurrent update and cancellation.

## Not in MVP

Case merging, organization workspaces, public search, reopening terminal cases.
