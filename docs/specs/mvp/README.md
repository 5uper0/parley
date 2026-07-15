# Consumer MVP — pre-code specification set

Status: **specified, not implemented**. These documents are the build contract for the convenient
consumer layer around the existing Parley engine. No module is implementation-ready unless its spec
below exists, names its trust boundary, and has testable acceptance criteria.

## Product promise

> Invite the other side. Each person privately states what they need and what they cannot accept.
> Parley proposes an agreement that crosses no red line, asks every party to ratify it, and produces
> a receipt each party can verify.

Parley is a neutral agreement tool, not a lawyer, court, debt collector, or source of legal advice.
It does not decide who is legally right and never presents an unratified proposal as an agreement.

## MVP user

An ordinary person resolving a documented, bounded dispute with one or more identifiable parties.
The first reference journey is an early lease exit; the product remains domain-neutral in code.

## End-to-end journey

1. Initiator creates a case and describes the decision in ordinary language.
2. Initiator invites the other parties through private, expiring links.
3. Each party independently completes a private elicitation interview and may attach evidence.
4. Each party reviews the structured position extracted from their words and explicitly confirms it.
5. Parley generates bounded candidate agreements from shared facts and confirmed private sheets.
6. The existing deterministic engine rejects red-line violations and ranks feasible options.
7. Parties see one proposal, accept, reject, or privately revise their own position.
8. Unanimous acceptance finalizes the agreement and emits a verifiable receipt.
9. Honest deadlock is a valid outcome; nobody is forced into an agreement.

## Module map

| # | Planned module | Owns |
|---|---|---|
| 01 | [Case lifecycle](01-case-lifecycle.md) | Case state machine and shared agenda |
| 02 | [Participant access](02-participant-access.md) | Invites, identity claims, session access |
| 03 | [Private elicitation](03-private-elicitation.md) | NL interview → owner-confirmed private sheet |
| 04 | [Evidence](04-evidence.md) | Files, shared facts, provenance and disclosure |
| 05 | [Proposal generation](05-proposal-generation.md) | Bounded candidate agreements as plain data |
| 06 | [Negotiation orchestration](06-negotiation-orchestration.md) | Rounds, engine calls, deadlock and revision |
| 07 | [Ratification](07-ratification.md) | Explicit accept/reject over an immutable proposal |
| 08 | [Receipt and export](08-receipt-export.md) | Human summary, transcript, verification and PDF |
| 09 | [Persistence and privacy](09-persistence-privacy.md) | Storage, encryption, retention and deletion |
| 10 | [Notifications](10-notifications.md) | Transactional invite and status delivery |
| 11 | [Billing](11-billing.md) | Paywall, entitlement and refund semantics |
| 12 | [Web client](12-web-client.md) | Accessible mobile-first user experience |

## Existing modules reused unchanged

`preferences.py`, `agent.py`, `consensus.py`, `transcript.py`, `spec.py`, and optional identity
signing remain the authority for non-betrayal. The MVP layer may prepare inputs and render outputs;
it may not reinterpret a red line, override deadlock, expose a private sheet, or manufacture an
acceptance.

## MVP scope

Included: one active case per purchase, 2–5 participants, asynchronous web flow, magic-link access,
text elicitation, common file attachments, one proposal at a time, up to three revision rounds,
unanimous ratification, verifiable web receipt and PDF export, email notifications, single-case
payment, English-first copy with locale-ready strings.

Excluded: legal conclusions, automatic contract enforcement, money transfer, e-signature status,
court filing, live mediator chat, voice calls, public case discovery, marketplace matching, native
apps, organizations/SSO, recurring subscriptions, A2A federation, and arbitrary LLM-generated code.

## Cross-module invariants

- Private positions are visible only to their owner-side service; other parties and the coordinator
  receive masked verdicts only.
- LLM output is untrusted draft data until the owner reviews and confirms it.
- Only declarative, schema-valid options enter the deterministic engine.
- Every acceptance binds the participant, proposal version, transcript hash, and timestamp.
- A changed proposal invalidates all earlier acceptances.
- No feasible option means honest deadlock, never a forced compromise.
- Evidence is private by default and becomes shared only through an explicit disclosure action.
- Product copy never claims legal validity, legal advice, or a guaranteed settlement.

## MVP success gate

- A first-time user creates and understands a case without assistance.
- Two participants complete the journey on mobile from invite to receipt.
- Neither participant can observe the other's private constraints or rejected reasons.
- A red-line-crossing option cannot be ratified through UI, API, retry, or stale state.
- At least one real bilateral case is unanimously ratified and both parties answer that the process
  was clearer or faster than their previous alternative.
- Median time from opening the invite to confirmed private position is under 10 minutes.

Implementation starts module-by-module only after this index and the relevant module spec are
accepted. Shipping the hosted paid product remains gated by demand validation in `docs/ROADMAP.md`.
