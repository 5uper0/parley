# 08 — Receipt and export

## Purpose

Turn an agreed result or honest deadlock into a human-readable artifact plus machine-verifiable
public data, without publishing private positions.

## Interface

- `build_receipt(case_id) -> Receipt`
- `verify_receipt(receipt) -> VerificationResult`
- `render_html(receipt_id) -> HTML`
- `render_pdf(receipt_id) -> PDF`
- `export_json(receipt_id) -> JSON`

## Receipt contents

Case title, participant display names and verification methods, shared facts, final proposal or
deadlock, ratification events, disclosed evidence hashes, masked transcript, transcript hash,
algorithm/version identifiers and limitations. It excludes raw interviews, sheets, violated red
lines, private notes and private evidence.

## Invariants

- Human summary is derived from the immutable structured result and cannot change obligations.
- JSON is canonical and verification works without trusting the hosted UI.
- PDF/HTML clearly distinguish `agreed`, `rejected`, `deadlocked` and `expired`.
- “Verified” means integrity, signatures and non-betrayal replay where available; it never means
  legally valid or factually true.

## Acceptance criteria

- Changing any covered field breaks verification.
- Receipt contains no known private marker fixture from any participant sheet.
- PDF is readable at mobile width, printable on A4 and tagged with status text, not color alone.
- Deadlock exports successfully without implying failure or blame.

## Not in MVP

Public blockchain anchoring, court-ready certification, public receipt discovery.
