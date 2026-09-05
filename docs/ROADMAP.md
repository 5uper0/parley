# Parley, hypothesis-driven roadmap

The MVP is confirmed: cross-owner group consensus among delegates with conflicting
private interests + deterministic red-line enforcement + verifiable transcript
(full test suite green, live 2- and 5-bot runs over HTTP). See [README](../README.md) for the
product one-liner.

**The main risk is NOT technology, it is monetization.** So this plan is
discovery-driven: cheap probes, feedback loops, don't build a paid product before we
find a segment that pays.

## Where the money is (money thesis, a hypothesis we test, not dogma)

1. **The consensus mechanism itself is $0.** Voting/consensus is a commodity (Snapshot is
   free). Don't sell the algorithm.
2. **WTP ∝ decision stakes × number of parties × need for privacy/neutrality/audit.**
   Lunch scheduling = $0. Multi-party negotiation where sides won't reveal positions to
   each other / to a human broker, and an auditable trail is required = real money.
3. **Revenue candidates (ranked, honest about how crowded each is):**
   - **B2B procurement / contract negotiation**, mature paying market (CLM / source-to-pay).
     Crowded (Spellbook/Icertis/…); our angle = the private+neutral+auditable multi-party
     consensus layer that CLM lacks.
   - **Auditable delegated governance** (committees, boards, grant/ethics panels,
     works-councils, DAOs), tamper-evident non-betrayal transcript = compliance artifact.
     Money = hosted trust-registry + audit + SLA.
   - **Managed hosting / trust-registry (open-core)**, OSS core free; paid = "safely meet
     agents from other orgs" relay + verified identities + SLA. Money in infra, not code.
4. **Differentiator vs Fetch.ai/Olas:** they monetize via token/take-rate; Parley =
   **no-crypto enterprise trust+audit+hosting**, sold to procurement/governance buyers who
   don't touch tokens. Hence "no blockchain" is a *product principle* (a hypothesis to test).

## The landscape (honest correction made mid-build)

"Nobody did this" is false. Prior art:
- **Single-owner orchestration** (AutoGen/CrewAI/LangGraph/Swarm), their "consensus" is
  proposer→judge verification within *one* owner. Not competitors.
- **Fetch.ai/Olas**, real prior art; bilateral commerce on-chain. Parley's wedge =
  multilateral (N>2) group-decision + conflict of interest + **no-crypto** + self-hosted +
  offline-arbitrable. Crypto agent tokens collapsed 89–99.7% → an argument *for* non-crypto.

## Roadmap, each step is hypothesis → test → signal → gate

- **Exp 0, Hardening + OSS-readiness (DONE).** Closed the demonstrated holes: signed
  verdicts (Ed25519), auth, rate-limit, validation; `probe.py` → a permanent red-team test.
  Gate met: 0 failing tests, the extraction attack no longer passes (401/429/sig).
  *Remaining sub-step: the actual public GitHub release, deliberately deferred until Exp 1
  produces one proof of value.*
- **Exp 1, Value (~1–2 wk).** NL-preference demo + run 1–2 **real** group decisions with
  real people (dogfood: family/team). Signal: do people feel the value of "private +
  auditable + I wasn't betrayed" vs Doodle/Slack?
  **Gate (one bar, both halves required):** real people ran a live decision through the tool,
  *each* of them ratified it against their own sheet, non-betrayal verified — **and** at least
  one of them said "this is better because …" in their own words.

  > **Corrected 2026-09-05.** This line used to state the gate as the quote alone, while the
  > Verification gates section below stated it as "real people ran a decision end-to-end, each
  > ratified". Two bars for one experiment. The weaker one was met by `dogfood-02` on 2026-07-22
  > and Exp 1 was recorded as closed, so the stronger one stopped being tracked and the software
  > that would have satisfied it went unwritten for seven weeks. `dogfood-02` is a **retrospective,
  > one-sided replay** — its own header says "not bilateral dogfood: the landlord has not reviewed
  > or ratified", so it cannot satisfy "real people, each ratified" and never could. It remains
  > genuine evidence of value and it closed HANDOFF gate #1, which is worded as the quote alone.
  > It does not close this one.
- **Exp 2, Segment/WTP (parallel, ~2 wk).** 8–12 problem interviews across candidates
  (procurement, agencies/SOW, committees/panels, DAOs). Signal: where do multi-party
  private negotiations cost real time/money today, and will they pay? **Gate: ≥1 segment
  with clear pain + budget.**
- **Exp 3, Differentiation (in the same interviews).** Test "no-blockchain, self-hosted,
  auditable" vs Fetch.ai/CLM. Signal: does neutrality+privacy+no-crypto matter?
- **Exp 4, Moat (later/parallel).** Deepen collusion-resistance ONLY once a paying segment
  is plausible. Start with an adversarial test of manipulating the max-min rule.

Every Exp has a kill/continue gate. Small balanced bets, feedback each cycle.

## Concrete next engineering steps (Exp 1)

- [x] `parley/elicit.py`, NL → PreferenceSheet, behind an LLM (hard/soft constraints). Merged
  2026-08-18 (#46).
- [x] `parley/ratify.py` + `examples/real_decision.py`, the end-to-end "run a decision with real
  people" flow with NL position entry and a human-ratification step. Merged 2026-09-05. **The
  engineering side of the Exp 1 gate is now complete: what remains is an operator action, not a
  build.** Run it with two or three real people who actually disagree about something, and the
  gate turns on one sentence from them.
- [ ] Multi-round counter-proposals in `parley/consensus.py` (not only scoring fixed options).
  **Deliberately not built yet** — nothing in the Exp 1 gate needs it, and building it before a
  real run tells us what to change is exactly the build-ahead-of-the-experiment failure mode this
  roadmap exists to prevent.
- [x] Tests: `tests/test_elicit.py`, `tests/test_ratify.py`, `tests/test_real_decision.py`.

## Verification gates

- **Exp 0:** `pytest -q` green; re-run `examples/redteam_probe_baseline.py` against a
  hardened bot, extraction blocked (401/429/signature); coordinator can't forge the
  transcript (verdict-signature check).
- **Exp 1:** real people ran a decision end-to-end, each ratified, non-betrayal verified, plus
  one "this is better because …" in a participant's own words. Identical to the gate stated on the
  Exp 1 line above — if these two ever diverge again, the divergence is the bug. Runnable since
  2026-09-05 via `examples/real_decision.py`; the receipt it writes is the artifact.

## Critical files

Modify: `parley/net/bot.py`, `parley/net/client.py`, `parley/transcript.py`,
`parley/consensus.py`. New: `parley/elicit.py`, `examples/real_decision.py`,
`tests/test_elicit.py`. Keep the core zero-dependency; crypto stays an optional extra.
