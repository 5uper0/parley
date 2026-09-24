# Changelog

Notable changes to Parley. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Entries cover
user-visible changes (library API, examples, live demo); routine doc and dependency commits are
omitted.

## [Unreleased]

### Added
- `parley/ratify.py`: an owner's explicit accept of a finished parley, bound to the decision and
  the transcript hash. `ratify()` refuses an accept that the submitted sheet rejects; `agreement()`
  is unanimous over one exact record and fails closed on a stale hash, a swapped decision, a
  rejection, a stranger or a missing owner. Unsigned acceptances are tamper-evidence only.
- `examples/real_decision.py`: the end-to-end flow for running a decision with real people at one
  keyboard. Public option set, private positions taken one person at a time, natural-language entry
  through `elicit` (or a manual mode with no model involved), then per-owner local ratification.
  The receipt reports unanimous acceptance and honest max-min separately.
- `parley/elicit.py`: natural-language → `PreferenceSheet` extraction behind a pluggable
  `Elicitor` interface — the LLM boundary stays outside the zero-dependency core (#46).
- `verify_outcome()` in `parley/consensus.py`: recompute the max-min result from the public
  transcript alone, so a coordinator cannot misreport the winner (v0.2 security fix 1 of 3) (#34).
- `--json` flag on `examples/run_env.py` for machine-readable consensus output (#31).
- Live demo: estate-valuation recipe made runnable, plus proof cards, recipe provenance, and
  SEO files (#42, #43).
- Live demo promoted to six scenarios with the Partnership and DAO treasury recipes (#18).
- Tests covering transcript tamper-evidence edge cases — first external contribution (#21).

### Changed
- A red-line predicate now passes only when it returns exactly `True`. Any other value crosses the
  red line, including truthy non-bools: `lambda o: o.get("flag")` used to pass on any non-empty
  value and now counts as a crossing. This is the change most likely to affect existing sheets —
  return a real `bool` from every predicate.
- `PreferenceSheet.evaluate()` raises `ValueError` when the utility returns NaN. The old clamp
  turned NaN into a score of 1.0.
- `run_consensus()` with no agents returns an honest deadlock instead of crashing, and refuses
  duplicate owner names or an unknown `rule` with `ValueError` before any agent is asked.
- `verify_outcome()` returns `False` when any entry is missing an owner's verdict, carries an
  owner twice, or has a different owner set from the other entries. Before, a coordinator could
  drop one owner's veto from the entry it wanted to win and the recomputation agreed with it.
- `verify_outcome()` takes an optional `expected_owners=`: when given, every entry's owner set must
  equal it exactly. Without it, a coordinator that drops one owner from every entry, or the lone
  veto in a one-option record, still passes. `scripts/verify-receipt.py` passes the receipt's
  `participants` (coordinator-written, as its output now says) and now names the owner-set mismatch
  explicitly (the existing roster check already failed such receipts). When `participants` is
  malformed, the max-min line fails as "owner set unchecked"; `participants: null` no longer
  crashes the script.
- `RemoteAgent.consider()` raises `ValueError` when the bot's card advertised a `pubkey_hex` and
  the reply carries a different key or no signature. Before, a party between the coordinator and a
  signed bot could sign verdicts with its own key and `verify_transcript()` accepted them. Bots
  whose card has no key are unaffected. The client checks that a signature is present under the
  card's key; whether the signature is valid is checked by `verify_transcript(require_signed=True)`,
  which `examples/run_env.py` now runs (exiting non-zero on failure) and any other caller must run.

### Fixed
- Static demo build now carries the proof cards and brand assets (#45).
- SHA-256 receipt hash wraps instead of overflowing its box (#19).

### CI
- Hosted demo builds and deploys on merge (#44); Python 3.14 added to the test matrix (#33);
  Dependabot version/security updates with patch/minor auto-merge (#22, #29).

## [0.1.0] - 2026-07-24

First tagged release. Repo went public 2026-07-18.

### Added
- Zero-dependency core: private `PreferenceSheet` with hard red lines as code predicates
  (`preferences.py`), masked `Verdict`s that never expose the sheet (`agent.py`), max-min
  consensus with honest deadlock (`consensus.py`), and a tamper-evident SHA-256 transcript
  with per-owner `verify_non_betrayal` replay (`transcript.py`).
- Networked mode: each bot as its own OS process behind a hardened HTTP server (`net/bot.py`),
  optional Ed25519-signed verdicts (`net/identity.py`), and a `RemoteAgent` client that makes
  the consensus core transport-agnostic (`net/client.py`).
- Runnable examples: `meeting.py` (in-process, with `--json`) and `run_env.py` (consensus over
  HTTP) (#5).
- Live demo at [parleyprotocol.com](https://parleyprotocol.com) with the committee grant vote
  recipe (#7).
- Site polish: footer, favicon, PWA manifest, `llms.txt` (#11, #12).

### Fixed
- Demo scenario tabs are keyboard-reachable with focus and key activation (#10).

[Unreleased]: https://github.com/5uper0/parley/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/5uper0/parley/releases/tag/v0.1.0
