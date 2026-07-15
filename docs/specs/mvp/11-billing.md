# 11 — Billing

## Purpose

Charge for opening a hosted settlement room without allowing payment status to influence consensus.

## MVP offer

One case purchase by the initiator. Participants join free. Price is configured externally; the
product displays the full amount before checkout. A case entitlement covers up to five parties,
three rounds, receipt hosting during retention and PDF/JSON exports.

## Interface

- `create_checkout(case_id, purchaser_id) -> Checkout`
- `handle_provider_event(event) -> Entitlement`
- `get_entitlement(case_id) -> Entitlement`
- `request_refund(case_id, reason) -> RefundState`

## Rules

- Draft creation is free; payment is required before invitations are sent.
- Provider-hosted checkout handles card data; Parley stores no PAN/CVC.
- Webhooks are signature-verified and idempotent.
- Payment failure pauses invitation, never deletes entered work.
- Suggested launch policy: full automatic refund if no other participant redeems an invite within
  seven days; deadlock itself is not a billing failure because it is an honest product outcome.

## Invariants

- Paid users receive no priority, weighting or constraint override.
- Billing metadata never enters proposal generation or consensus.
- A refund cannot erase an already issued receipt or rewrite case history.

## Acceptance criteria

- Duplicate/out-of-order webhooks produce one entitlement.
- Checkout, success, failure and refund states are recoverable after browser closure.
- Currency, tax and total are visible before payment.
- Sandbox integration tests cover success, failure, replay and refund.

## Not in MVP

Subscriptions, split payments, escrow, payouts, coupons, usage billing, enterprise invoices.
