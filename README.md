<div align="center">

# parley.

### The trust layer for the agent economy

**Provable consensus for AI agents of rival owners**, deterministic red lines, max-min consensus over
masked verdicts, and a verifiable non-betrayal transcript.
<br>Multilateral (N&gt;2) · non-crypto · self-hosted · Apache-2.0.

[![ci](https://github.com/5uper0/parley/actions/workflows/ci.yml/badge.svg)](https://github.com/5uper0/parley/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
![core](https://img.shields.io/badge/core-zero--dependency-informational.svg)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[Try it live](https://parleyprotocol.com/demo/)** · **[See it in 30 seconds](#see-it-in-30-seconds)** · [Roadmap](docs/ROADMAP.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

<br>

<img src="docs/brand/assets/parley-money-shot.gif" alt="Parley money-shot: three rival parties reach a max-min decision, a red-line-crossing shortcut is BLOCKED in code, and every party verifies a tamper-evident SHA-256 receipt" width="760">

<sub>Rival parties reach a max-min decision · a shortcut that would cheat someone is **BLOCKED** by a red line · every party verifies the tamper-evident receipt.</sub>

</div>

---

## Install

```bash
pip install parley-consensus              # zero-dependency core
pip install "parley-consensus[crypto]"    # + Ed25519-signed verdicts (parley.net.identity, parley.net.bot)
```

The distribution is `parley-consensus` (PyPI's `parley` is an unrelated project); the import name is `parley`.

```python
from parley.agent import Agent
from parley.consensus import run_consensus
from parley.preferences import HardConstraint, PreferenceSheet

options = [{"venue": "rooftop", "cost": 900}, {"venue": "garden", "cost": 600}, {"venue": "diner", "cost": 300}]
ana = PreferenceSheet("Ana", utility=lambda o: 1.0 if o["venue"] == "rooftop" else 0.4)
bob = PreferenceSheet("Bob", hard=[HardConstraint("budget", lambda o: o["cost"] <= 700)],  # a red line: code, not a preference
                      utility=lambda o: 1 - o["cost"] / 1000)
cara = PreferenceSheet("Cara", utility=lambda o: 0.9 if o["venue"] == "garden" else 0.5)

result = run_consensus([Agent(s.owner, s) for s in (ana, bob, cara)], options)
print(result.status, result.decision)
print("receipt sha256:", result.transcript.hash())
for sheet in (ana, bob, cara):  # each owner replays their own private sheet, locally
    print(sheet.owner, "not betrayed:", result.transcript.verify_non_betrayal(sheet, result.decision))
```

```
agreed {'venue': 'garden', 'cost': 600}
receipt sha256: a9cb75c0a15b41360fb2b134e084ca3b577daaf50f5edb657c5c4da43cc2fc72
Ana not betrayed: True
Bob not betrayed: True
Cara not betrayed: True
```

The rooftop is Ana's favourite and loses anyway: it crosses Bob's budget red line, so it is rejected
before any score is weighed. The coordinator only ever saw `red-line`, never the budget or the sheet.

Contributors install from a clone instead: `pip install -e ".[dev]"` (see [Status](#status-v0-working-core)).

### Use it from an MCP host (Claude, Cursor)

<!-- mcp-name: io.github.5uper0/parley -->

The base install ships a stdlib-only MCP server over stdio. Point your host at it:

```json
{"mcpServers": {"parley": {"command": "parley-mcp"}}}
```

If the console script is not on the host's `PATH`, launch it through the interpreter that has
the package: `{"command": "python", "args": ["-m", "parley.mcp"]}`.

Three tools appear: `parley_decide` (options + each party's red lines and preferences in,
`status`, `decision`, `transcript` and `transcript_sha256` out), `parley_verify_receipt`
(recompute the hash over a transcript, and recompute the max-min decision from its recorded
verdicts) and `parley_check_party` (replay one party's red lines against a decision). The input
is the same JSON as the recipes in [`examples/demo/`](examples/demo/). Example prompt:

> Three of us are picking a venue: rooftop (900), garden (600), diner (300). Bob will not go over
> 700; Ana prefers the rooftop, Cara the garden, Bob the cheapest. Use parley_decide, then verify
> the receipt hash and check that Bob's red line held.

**What this mode does and does not give you.** The host holds every party's spec and passes them
all in one call, so there is no privacy between parties or from the host. What still holds is
what the engine enforces in code: a red line rejects an option deterministically, the max-min
rule picks among options feasible for everyone, and the receipt hash makes any later edit to the
transcript visible, provided the hash is kept by someone other than whoever might edit the
transcript: it is unsigned and the server does not store it, so a hash and a transcript from the
same hand prove nothing about each other. `max_min_verified` does not depend on the hash: it
recomputes the winner from the recorded verdicts. For private sheets, run one process per owner over HTTP
([`examples/run_env.py`](examples/run_env.py)); the coordinator then sees only masked verdicts.

---

Most agent tooling in 2026 solves either transport/identity (A2A, MCP) or 1:1 agentic
commerce (an agent buys/books for you), or *cooperative* debate between agents of the
**same** owner. Parley targets the gap nobody productised: a group of delegates, each
representing a **different** principal with **conflicting** and **private** interests,
reaching a decision everyone can trust, and *prove* their agent didn't betray them.

**Who it's for.** Teams and platforms where several parties must reach a decision none of them can
rig, and prove it afterward. Built first for **regulated, multi-party workflows**: compliance &
onboarding decisions (KYC/AML, sanctions red lines), marketplace & P2P disputes, and delegated
governance (committees, panels).

The wedge is three properties, enforced in code rather than left to an LLM's discretion:

1. **Deterministic red lines.** Each owner's hard constraints are predicates checked in
   code. A proposal that crosses one is *rejected*, never negotiated away. "My agent
   won't betray me" becomes a provable property, not a hope.
2. **Conflicting-interest consensus.** The coordinator sees only masked verdicts, a
   feasibility flag, a soft score, and a *masked* reason (`ok`/`red-line`), never the
   private sheets or which constraint was at stake. A decision must be feasible for *every* agent; among those it
   picks by an egalitarian max-min rule (lift the least-happy participant), tie-broken by
   total welfare, social choice, not majority vote. No feasible option ⇒ honest deadlock.
3. **Verifiable transcript.** A tamper-evident SHA-256 record of every masked verdict.
   Each owner can replay their *own* private sheet locally to prove no red line was
   crossed, without revealing the sheet to anyone.

## Why this exists (and what we learned building it)

Agents are starting to act on our behalf: booking, negotiating, onboarding, allocating. The moment
two agents serve **different** owners, "did my agent sell me out?" stops being paranoia and becomes a
real question. The crypto answer to agent-trust (put it on a chain, add a token) collapsed 89–99.7%;
the durable need is the **trust primitive itself**, decoupled from tokens.

> **AI that can't lie, and you can check.** The 2026 agent-hype cycle proved virality can be
> fully decoupled from truth. Parley is the provable version: every verdict in a parley is a
> re-hashable receipt, and each owner replays their own private sheet to prove no red line was
> crossed, no trust required, just the check.

Building the v0 taught us the wedge is narrower and sharper than "multi-agent consensus": the value
isn't the vote, voting is free (Snapshot, polls). The value is **provable non-betrayal under
conflicting private interests**, that no party had to reveal their private sheet or which red line
was at stake, no red line could be traded away, and everyone can check the receipt themselves. That's what doesn't compose from off-the-shelf
parts, and it's the one thing we made enforceable in code rather than left to an LLM's goodwill. The
worked proof: [`docs/dogfood-01-p2p-escrow.md`](docs/dogfood-01-p2p-escrow.md).

## Status: v0 (working core)

Pure-stdlib, zero-dependency core. In-process transport with a clean seam where **A2A**
(distributed discovery + signed Agent Cards) drops in next. LLM-elicited preference sheets
(`parley/elicit.py`) and Ed25519-signed transcripts (`parley/net/identity.py`, optional
`crypto` extra) already ship. This v0 deliberately isolates the novel part, the consensus +
non-betrayal, and reuses nothing that's already a commodity.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q                     # the full suite, all green
.venv/bin/python examples/demo/server.py   # the money-shot: open http://127.0.0.1:8080 → Run
.venv/bin/python examples/meeting.py    # three delegates pick a meeting slot
.venv/bin/python examples/run_env.py    # bots as separate processes, consensus over HTTP
.venv/bin/python examples/real_decision.py --options examples/demo/recipe_committee.json
                                        # run a real decision with real people, each one ratifies
```

### See it in 30 seconds

`examples/demo/server.py` runs the *real* engine behind one web page:
rival parties, a max-min decision, one option **BLOCKED** by a red line, and a re-hashable receipt
each party verifies privately. A worked example, a P2P escrow dispute end-to-end, with the
per-party "this is better because…", is in [`docs/dogfood-01-p2p-escrow.md`](docs/dogfood-01-p2p-escrow.md)
(synthetic). A **real, anonymized** dispute, a retrospective early-lease-exit replay where the tenant
ratified a "this would have been better" outcome, is in
[`docs/dogfood-02-early-lease-exit.md`](docs/dogfood-02-early-lease-exit.md) (honest boundary: the
landlord side is inferred, not ratified). The screenshot-native proof card is `examples/demo/proofcard_p2p.html`.

**No Python? Run the demo with Docker:**

```bash
docker build -t parley . && docker run --rm -p 8080:8080 parley   # open http://127.0.0.1:8080
```

**Try it live: [parleyprotocol.com/demo](https://parleyprotocol.com/demo/)** runs the real engine
behind one web page, no install and nothing to sign up for. Prefer to self-host? The repo ships a
`Dockerfile` (and a `render.yaml` Blueprint) so you can run the same demo anywhere in one command.

## Built by an agent fleet

The product is **trust between agents of different owners**. It was *made* by a fleet of one owner's
agents: they plan, write the code, review each other, and ship behind a hard gate, a human directs
and holds the irreversible gates (going public, outreach), the fleet does the engineering. Every
change clears the same gate you can run yourself: `scripts/ship-gate.sh`, tests green,
zero-dependency core, examples run, under conventional-commit discipline.

## Security (v0.1)

The net layer is hardened against the obvious attacks (see `tests/test_redteam.py`):

- **Signed verdicts (Ed25519).** Each bot signs its verdict over the specific option, binding the
  content to a key. `verify_transcript(require_signed=True)` then rejects any verdict that was
  altered, or that arrives unsigned when a signature was expected. **Scope (read this):** the check
  proves each signature is internally consistent with the pubkey *carried in that record*. It does
  **not** yet prove *authenticity*, that the pubkey is the owner's real key, because there is no
  trusted `owner → key` roster: a coordinator that assembles the transcript could substitute its own
  keypair. Treat signatures today as **tamper-evidence**, not third-party-provable identity.
- **Auth + rate limiting + input validation.** Without a bearer token `/consider` returns 401;
  brute-force enumeration is throttled (429); oversized/malformed bodies are rejected (413/400).
  This closes the preference-extraction hole (an unauthenticated attacker previously reconstructed
  a bot's private red line by probing).
- **Outcome verification.** `verify_outcome(transcript)` (in `parley.consensus`) recomputes the
  max-min winner from the recorded verdicts and checks it matches the announced decision, so a
  coordinator that finalizes a *feasible-but-not-max-min* (or infeasible) option is caught. Anyone
  can replay it over the public record — no private sheet needed. Pass
  `expected_owners=` the roster you expect, or a coordinator that drops one owner from every entry
  still passes. (`verify_non_betrayal` still only proves your *own* red lines held.)

Not yet (v0.1 honest limits, do not treat as production-secure for adversarial principals):
- **Authenticity pinning**, signatures verify against a self-asserted key, not a trusted roster
  (above); the roster-pinned check (verify against the key from each bot's discovery Agent Card) is v0.2.
  Today only the coordinator's own side pins it: the client checks that a signature is present
  under the card's key; whether the signature is valid is checked by
  `verify_transcript(require_signed=True)`, which `examples/run_env.py` now runs and any other
  caller must run.
- **Replay binding**, verdicts carry no session/nonce, so a signed verdict is replayable into another
  parley that reuses the same option.
- **Range-masked scores**, the soft cardinal `score` is public in the transcript, so an untrusted
  coordinator can infer preference *ordering* and each party's feasible region (the *reason* and the
  private sheet stay hidden; MPC/range-masking is future work).
- **TLS/mTLS**, and game-theoretic **collusion / strategic-misreport resistance** (the research track).

The hosted demo at [parleyprotocol.com](https://parleyprotocol.com) uses GA4 for basic traffic
analytics — see [what's collected](https://parleyprotocol.com/privacy). The protocol and the
self-hosted `docker run` path collect nothing.

## Where's the money (open-core thesis)

The consensus mechanism itself is a commodity (voting/consensus is free, Snapshot, polls). Value,
and willingness to pay, scales with **decision stakes × number of parties × need for privacy /
neutrality / audit**. The paid layer is the *trusted neutral broker*: hosted identity/trust-registry,
audit-grade signed transcripts, and managed self-hosting, not the algorithm. First candidate
segments: private multi-party B2B negotiation (procurement/SOW) and auditable delegated governance
(committees, panels). Differentiator vs **Fetch.ai / Olas** (real prior art): they do *bilateral*
commerce on a *blockchain*; Parley does *multilateral group consensus*, provable non-betrayal,
**no crypto**, self-hosted.

The demo shows three people whose agents hold private, conflicting constraints reach a
slot everyone's red lines allow, then each owner proves non-betrayal, and a second run
that hits an honest deadlock instead of forcing a bad decision.

## Architecture

| Layer | v0 | Next |
|-------|----|------|
| Transport / discovery / identity | in-process | **A2A** (signed Agent Cards, mDNS/registry), *reuse, don't rebuild* |
| Agent brain | pure code, or `parley/elicit.py` (LLM drafts, participant confirms) | wider elicitation UX |
| **Red-line enforcement** | `parley/preferences.py` (code predicates) | the core; stays deterministic |
| **Consensus** | `parley/consensus.py` (max-min) | Nash bargaining, weighted rules |
| **Verifiability** | `parley/transcript.py` (hash + local replay), optional Ed25519 signing | range-masked scores (MPC) |
| Adversarial | N/A | **Byzantine/collusion resistance**, the research-grade contribution |

## Roadmap → open-core

- **Now:** consensus core + red-line guard + verifiable transcript (this repo, Apache-2.0).
- **Next:** A2A transport so agents on different machines discover and parley over a LAN.
  (LLM-elicited sheets and Ed25519-signed transcripts already ship.)
- **Research:** inject a lying/colluding agent and show max-min + Byzantine-robust
  aggregation resists it. This is the part potentially interesting to frontier R&D.
- **Paid (self-host):** hosted relay/trust-registry so agents meet safely beyond the LAN,
  plus managed hosting of agents on your own hardware. Open-source core, paid federation.

First ICP: a **closed group** (a team/department/family) where one operator deploys all
the agents, sidesteps the cold-start network effect. "Delegate the position to your
agent, agents find the common decision" is exactly this.

## Contributing

The core is small on purpose; the best contributions right now are **adversarial tests** and a
second opinion on the consensus protocol. Start with [CONTRIBUTING.md](CONTRIBUTING.md), file a bug
with a reproducing recipe, or open a discussion. Six small, single-file tasks (type hints, tests,
a CI check) are open under [good first issue](https://github.com/5uper0/parley/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
Report security issues privately via [SECURITY.md](SECURITY.md).

## Star history

If Parley's approach to provable non-betrayal is interesting, a star helps others find it.

<!-- Renders once the repo is public: -->
[![Star History Chart](https://api.star-history.com/svg?repos=5uper0/parley&type=Date)](https://star-history.com/#5uper0/parley&Date)

## License
Apache-2.0, permissive, with an explicit patent grant (clears enterprise legal review). See [LICENSE](LICENSE) + [NOTICE](NOTICE).
