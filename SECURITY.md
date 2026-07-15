# Security policy

Parley's reason to exist is that its guarantees are *checkable*, so we take reports about broken
guarantees as seriously as classic vulnerabilities.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.** Use GitHub's private
[Report a vulnerability](https://github.com/5uper0/parley/security/advisories/new) flow, or email
**oleh@veheria.tech**. We aim to acknowledge within 72 hours.

Things we especially want to hear about:

- A way to make a red-line-violating option **win** (a betrayal that the engine accepts).
- A way for an untrusted coordinator to **forge or replay** a signed verdict past
  `verify_transcript()`.
- A way to **extract a private preference sheet** through the net layer (the extraction attack the
  red-team tests are meant to close — see `tests/test_redteam.py`).
- Any way to make `verify_non_betrayal` return a false ✓.

## Scope & maturity

This is a **v0**. The net layer is hardened against the demonstrated attacks (Ed25519-signed
verdicts, bearer auth, rate limiting, input validation). Known limits we already disclose (so a
report on one of these is a confirmation, not a surprise — but a *working exploit or a sharper
framing* is still welcome):

- **Signatures are tamper-evidence, not authenticity.** `verify_transcript` checks each signature
  against the pubkey carried *in the same record*; there is no trusted `owner → key` roster yet, so a
  coordinator that assembles the transcript could sign a fabricated verdict with its own key. The
  roster-pinned check (pin each owner's key from its `/card`) lands in v0.2.
- **No replay binding.** Verdict payloads carry no session id or nonce, so a genuine signed verdict
  is replayable into another parley that reuses the same option.
- **No outcome verification.** Nothing recomputes the max-min winner from the transcript;
  `verify_non_betrayal` only proves *your own* red lines held on the announced decision, not that the
  coordinator selected the honest max-min option.
- **Scores are unmasked.** The soft cardinal `score` is public, leaking preference ordering / feasible
  region (range-masking via MPC is future work).
- **No TLS/mTLS**, and no game-theoretic **collusion / strategic-misreport resistance** (research track).

Do not deploy v0 against genuinely adversarial principals in production. Reports that deepen the
collusion-resistance story, or that break a guarantee we *didn't* list above, are the ones we most
want — the first four items are on the v0.2 roadmap.

## Supported versions

Until a `1.0` tag, only the `main` branch is supported. Fixes land on `main`.
