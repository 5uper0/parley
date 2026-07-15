# 02 — Participant access

## Purpose

Let ordinary users enter a specific case without passwords while preventing invite forwarding,
cross-case access, and identity ambiguity.

## Interface

- `issue_invite(case_id, participant_id) -> InviteToken`
- `redeem_invite(token, email_challenge) -> Session`
- `refresh_session(session_id) -> Session`
- `revoke_participant(case_id, participant_id)`

## Rules

- Invite tokens are single-purpose, hashed at rest, expire after 72 hours, and become bound to the
  verified email after first redemption.
- Sessions are case- and participant-scoped, HttpOnly, Secure and SameSite cookies; no bearer token
  is stored in browser-readable storage.
- Reissuing an invite revokes the previous unredeemed token.
- Ratification requires a fresh email challenge if the session is older than 30 minutes.

## Invariants

- A participant can access only their own private workspace and the shared case view.
- Display names are not identity proof; the receipt states the verification method used.
- Removing a participant before proposal generation invalidates case readiness.

## Acceptance criteria

- Expired, reused, revoked and cross-case tokens are rejected.
- A forwarded link cannot be ratified without control of the invited email.
- Session expiry preserves saved work and returns the user to verification.
- Rate limits apply to token redemption and email challenges.

## Not in MVP

Passwords, social login, government identity, KYC, SSO, delegated representatives.
