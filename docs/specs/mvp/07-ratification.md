# 07 — Ratification

> **Status:** target spec for the ratification **UI**, not a description of shipped behaviour. The
> shipped primitive is `parley/ratify.py` (`ratify`, `agreement`): hash- and decision-bound,
> unanimous, optionally signed against a self-attested key. Cross-participant binding
> (an acceptance attributable to a known owner key) lands with the v0.2 roster pin — see
> `SECURITY.md`.

## Purpose

Collect an explicit, informed accept/reject decision from every participant over one immutable
proposal, attributable to that participant once the v0.2 roster pin lands.

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

- Stale-hash and replayed acceptance attempts fail (shipped). Cross-participant attempts fail
  once acceptances are checked against the roster-pinned owner key (v0.2).
- Users can download/read the proposal before deciding.
- Agreement finalizes exactly once under concurrent final acceptances.
- Tests cover reject, expiry, stale proposal, unanimous finalization and accessibility labels.

## Not in MVP

Qualified e-signatures, notarization, legal enforceability claims, partial-party agreements.
