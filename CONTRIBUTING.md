# Contributing to Parley

Parley is early and the core is small on purpose. The best contributions right now are
sharp questions, adversarial tests, and a second opinion on the consensus protocol.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"    # core is zero-dep; dev adds pytest + pynacl
.venv/bin/pytest -q                   # all tests must be green
.venv/bin/python examples/meeting.py  # local demo
.venv/bin/python examples/run_env.py  # bots as separate processes over HTTP
```

## Ground rules

- **Tests first.** Every behavior change ships with a test. The whole point of Parley is
  that its guarantees are *checkable*, a change without a test can't demonstrate its guarantee.
- **Keep the core zero-dependency.** `parley/` (preferences, agent, consensus, transcript)
  must import only the stdlib. Anything needing a library (crypto, HTTP clients, LLMs) goes
  behind an optional extra and lives in a submodule (see `parley/net/`).
- **Never weaken a security property silently.** If a change touches signing, auth, rate
  limiting, or the red-line guard, add/extend a `tests/test_redteam.py` case proving the
  property still holds.
- **Small, readable diffs.** Match the surrounding style; comment only to state a constraint
  the code can't show.

## Good first issues

Scoped, single-file tasks are tracked under the [`good first issue`](https://github.com/5uper0/parley/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
label — typing passes, edge-case tests, new decision recipes. Comment on one to claim it.

Larger tracks (adversarial tests against the consensus protocol, an A2A-native transport
adapter, natural-language → `PreferenceSheet` elicitation) are on the roadmap rather than
ready to pick up — open an issue to discuss before starting one.

## Scope

Parley is the *consensus + trust* layer, not a transport or an agent framework. Transport
should ride existing standards (A2A). Please open an issue to discuss before large additions.
