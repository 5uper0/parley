# Dogfood #01, P2P escrow dispute (synthetic demo proof)

> **⚠️ This is a DEMO proof, not a paying-client case.** A **synthetic but realistic** scenario on
> the crypto/P2P + KYC beachhead, flagged honestly. It proves the mechanism end-to-end on the real
> engine. A **real dogfood with a real party remains the strongest proof** and, when available,
> supersedes this. Do not present this as "a customer paid us."

## The scenario (the beachhead: crypto/P2P dispute resolution)

A peer-to-peer marketplace escrow dispute, the exact shape our first ICP lives in. Money is locked
in escrow; three parties with **conflicting, private** interests must reach one outcome:

| Party | Private interest (never revealed to the others) |
|---|---|
| **Buyer** | wants the refund, utility rises with their share |
| **Seller** | wants the release, utility rises with their share |
| **Platform** | a **red line**: no payout may skip evidence review (fraud/chargeback exposure) |

Four options on the table: release-to-seller (0/100), split (50/50), refund-buyer (100/0), and a
tempting shortcut, **instant refund, skip evidence**.

## The run (real engine, `examples/demo/recipe_p2p_dispute.json`)

Run it yourself: `python examples/demo/server.py` → open the page → **Run**. Or headless:
`python examples/demo/proofcard.py examples/demo/recipe_p2p_dispute.json`.

```
status:        agreed
decision:      Split the escrow (50/50)
per-option floor (max-min):
  Release to seller (0/100)      feasible=True   floor=0.0
  Split the escrow (50/50)       feasible=True   floor=0.5   ← chosen
  Refund the buyer (100/0)       feasible=True   floor=0.0
  Instant refund, skip evidence  feasible=False  (BLOCKED, Platform red line)
non-betrayal replay:  Buyer ✓   Seller ✓   Platform ✓
transcript sha256:    b41b05954802aa4f5d83…
```

Three things happened that are **enforced in code, not by an LLM's goodwill**:

1. **The shortcut was rejected, full stop.** "Instant refund, skip evidence" is infeasible because it
   crosses the Platform's deterministic red line, it can never win, regardless of how much anyone
   wants it. Not negotiated away; *rejected as a code predicate*.
2. **The floor was lifted (Rawlsian max-min).** Both one-sided payouts (0/100, 100/0) leave the
   losing party at floor **0.0**. The 50/50 split lifts the least-happy party to **0.5**, so the
   engine picks it. Not majority vote; the *least-happy participant* is maximized.
3. **Every party can prove they weren't betrayed.** Each replays their **own private sheet** against
   the final decision locally (`verify_non_betrayal`), all three return ✓, and the whole record is
   a tamper-evident SHA-256 transcript anyone can re-hash. No red line was crossed; nobody has to
   trust the coordinator.

## "This is better because…" (the articulation gate #1 asks for)

Framed per party, against the status quo they actually use today (a human arbitrator, a Discord mod,
or an on-chain vote):

- **Buyer / Seller:** *"I never had to show the other side my real bottom line, and I can check,
  mathematically, on my own machine, that the outcome didn't cross my hard limit. A human mediator
  asks me to reveal my position and then I just have to trust them."*
- **Platform:** *"My compliance red line (evidence review) is enforced in code, it literally cannot
  be traded away in a negotiation, and I have a signed, re-hashable receipt for the auditor. Today
  that guarantee is a policy doc and a hope."*
- **Why not on-chain?** No token, no gas, self-hosted, and the losing side can take the same
  transcript to an offline arbitrator. The crypto answer to agent-trust collapsed 89–99.7%; the
  durable need is the **trust primitive**, decoupled from tokens.

**The one-liner:** *Doodle/Slack/a human broker give you an outcome. Parley gives you an outcome plus
a proof, that no one's red line was crossed and the least-happy party was lifted, that each side
verifies privately, without revealing their hand.*

## Honest caveat + what the real dogfood adds

This proves the **mechanism** (feasibility, floor-lift, blocking, verifiable non-betrayal) on a
realistic scenario. It does **not** prove **demand**, that a real party in a real dispute felt the
pain and would pay. That is exactly what a real-party dogfood and problem interviews test.
When a real case is available, we swap the recipe, re-run, and capture a *real* person's
quote, which then replaces this section's articulation in the README narrative.

**Shareable asset:** `examples/demo/proofcard_p2p.html` (a screenshot-native proof card from this
exact run, README/social unit).
