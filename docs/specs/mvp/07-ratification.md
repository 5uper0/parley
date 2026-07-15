# 07 — Ratification

## Purpose

Collect an explicit, informed and attributable accept/reject decision from every participant over
one immutable proposal.

## Interface

- `present(proposal_id, participant_id) -> RatificationView`
- `accept(proposal_id, participant_id, proposal_hash, challenge) -> Acceptance`
- `reject(proposal_id, participant_id, category, private_note=None) -> Rejection`
- `status(proposal_id) -> RatificationStatus`

## Rules

- View shows concrete obligations, dates, amounts, disclosed evidence, known uncertainties, and a
  plain statement that Parley is not legal advice.
- Accept requires scrolling/expanding the complete proposal, a fresh access challenge, and an
  unambiguous button. Reject never requires explanation.
- Agreement requires unanimous acceptance from the current participant set.
- A rejection ends ratification and may open a new revision round if rounds remain.

## Invariants

- Acceptance binds participant, proposal hash, transcript hash, case version, sheet version and time.
- Any content or participant change invalidates every prior acceptance.
- Silence, email open, timeout or partial completion is never acceptance.
- UI cannot accept an option that failed deterministic feasibility.

## Acceptance criteria

- Stale-hash, replayed and cross-participant acceptance attempts fail.
- Users can download/read the proposal before deciding.
- Agreement finalizes exactly once under concurrent final acceptances.
- Tests cover reject, expiry, stale proposal, unanimous finalization and accessibility labels.

## Not in MVP

Qualified e-signatures, notarization, legal enforceability claims, partial-party agreements.
