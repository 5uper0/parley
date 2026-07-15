<!-- Thanks for contributing to Parley. Keep changes to one logical thing. -->

## What & why

<!-- What does this change and why? Link the issue if there is one. -->

## Guarantees checklist

- [ ] `pytest -q` is green.
- [ ] The `parley/` core stays **zero-dependency** (any crypto/LLM code is behind an optional extra).
- [ ] This does **not** weaken the core properties: deterministic red lines, masked verdicts,
      max-min consensus, or the verifiable non-betrayal transcript.
- [ ] Behaviour changes ship with a test that demonstrates the new guarantee.

## Proof

<!-- Paste the relevant test run, the demo output, or the recipe that exercises this. -->
