# 10 — Notifications

## Purpose

Deliver transactional progress without leaking case substance into email or turning reminders into
pressure to accept.

## Events

Invite, invite reminder, all parties joined, private position requested/confirmed, proposal ready,
proposal rejected, agreement reached, deadlock, expiry warning and receipt ready.

## Interface

- `enqueue(event, recipient, case_id, dedupe_key)`
- `deliver(notification_id)`
- `record_delivery(provider_event)`
- `preferences(participant_id)` for optional reminders

## Invariants

- Email contains case title and action link only; never constraints, scores, proposal terms or
  another party's activity details.
- Transactional delivery cannot be used to infer why an option failed.
- Reminders ask the user to review, never to accept; maximum two reminders per pending action.
- Links use participant access tokens governed by spec 02.

## Acceptance criteria

- Delivery is idempotent by dedupe key and retries with bounded backoff.
- Bounces are recorded without blocking other participants.
- Users can disable reminders but not security or final-status messages.
- Templates are locale-ready, plain-text compatible and accessible.

## Not in MVP

SMS, push, WhatsApp/Telegram, marketing campaigns, negotiation content in email.
