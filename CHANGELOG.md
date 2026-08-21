# Changelog

Notable changes to Parley. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Entries cover
user-visible changes (library API, examples, live demo); routine doc and dependency commits are
omitted.

## [Unreleased]

### Added
- `parley/elicit.py`: natural-language → `PreferenceSheet` extraction behind a pluggable
  `Elicitor` interface — the LLM boundary stays outside the zero-dependency core (#46).
- `verify_outcome()` in `parley/consensus.py`: recompute the max-min result from the public
  transcript alone, so a coordinator cannot misreport the winner (v0.2 security fix 1 of 3) (#34).
- `--json` flag on `examples/run_env.py` for machine-readable consensus output (#31).
- Live demo: estate-valuation recipe made runnable, plus proof cards, recipe provenance, and
  SEO files (#42, #43).
- Tests covering transcript tamper-evidence edge cases — first external contribution (#21).

### Fixed
- Static demo build now carries the proof cards and brand assets (#45).

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
- Live demo at [parleyprotocol.com](https://parleyprotocol.com) with six scenarios, including
  committee grant vote, partnership, and DAO treasury recipes (#7, #18).
- Site polish: footer, favicon, PWA manifest, `llms.txt` (#11, #12).

### Fixed
- Demo scenario tabs are keyboard-reachable with focus and key activation (#10).
- SHA-256 receipt hash wraps instead of overflowing its box (#19).

[Unreleased]: https://github.com/5uper0/parley/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/5uper0/parley/releases/tag/v0.1.0
