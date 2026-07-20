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

- Adversarial tests against the consensus protocol (strategic misreporting, (N−1)-vs-1 collusion).
- An A2A-native transport adapter alongside the current HTTP one.
- Natural-language → `PreferenceSheet` elicitation (behind an LLM extra).

## Scope

Parley is the *consensus + trust* layer, not a transport or an agent framework. Transport
should ride existing standards (A2A). Please open an issue to discuss before large additions.
