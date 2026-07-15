# 09 — Persistence and privacy

## Purpose

Persist hosted cases without turning the coordinator database into a collection of everyone's
negotiating limits.

## Storage split

- Shared store: case metadata, participants, shared facts, options, masked verdicts, receipts.
- Owner-private store: raw interview, private evidence, sheet and revision history, encrypted with a
  participant-scoped data key.
- Secret store: invite hashes, signing keys and provider credentials; never application logs.

## Interface

- repositories expose versioned `get`, `append_event`, `put_private`, `get_private`, `delete_case`;
  business modules do not execute ad hoc cross-boundary queries.
- `request_deletion(case_id, participant_id)` and `expire_cases(now)` implement retention policy.

## Invariants

- Coordinator-facing code cannot query private sheet content across participants.
- Encryption in transit and at rest; sensitive fields are excluded from logs, analytics and errors.
- Default retention: unfinished case 30 days after inactivity; terminal case 90 days unless all
  participants choose earlier deletion. Receipts can be downloaded before deletion.
- Backups follow the same retention and encryption boundaries.
- Deletion is auditable and removes keys so retained ciphertext is unreadable.

## Acceptance criteria

- Authorization tests prove tenant isolation across cases and participants.
- Logs contain no raw answers, invite tokens, sheet values or document contents.
- Restore test preserves event order and receipt verification.
- Deletion and expiry tests cover primary store, objects, search indexes and backup tombstones.

## Not in MVP

Regional residency controls, customer-managed keys, enterprise retention policies, SOC 2 claims.
