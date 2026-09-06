# Parley — press kit

*Source of truth for anything a journalist, podcast host, awards jury, accelerator or investor
needs about Parley. Every number here is checked against the repository, not the pitch. Last
verified 2026-09-05.*

Public page: <https://parleyprotocol.com/press/> · Repository: <https://github.com/5uper0/parley>

---

## 1. Boilerplate

**One line (under 100 characters)**
> Parley is the neutral referee for AI agents that represent people with conflicting interests.

**Short (50 words)**
> Parley is an open-source consensus layer for AI agents that act on behalf of different owners.
> Each owner's red lines are enforced as code, not as a model's good intentions. Agents exchange
> masked verdicts, a max-min rule picks the option that lifts the least-happy party, and every
> decision leaves a transcript each owner can verify alone.

**Medium (100 words)**
> When two organisations both put an AI agent in the room, someone has to referee. Parley is the
> open-source layer that does it. Owners write private preference sheets whose hard constraints are
> executable predicates, so a violating option cannot win regardless of what any model argues.
> Agents reveal only a masked verdict: acceptable or not, a soft score, and a reason reduced to
> "ok" or "red-line". Consensus is max-min, so the least satisfied participant is lifted rather
> than outvoted. Every run produces a hash-chained transcript with optional Ed25519 signatures that
> each owner replays against their own private sheet. Multilateral, non-crypto, self-hosted.

**Long (150 words)**
> The agent ecosystem standardised how agents talk to each other. It left open what happens when
> two agents want opposite things on behalf of rival owners. Parley fills that gap.
>
> An owner writes a preference sheet with two kinds of entries: soft preferences that carry a score,
> and hard red lines that are code predicates. A red line rejects an option outright, so
> non-betrayal is a property of the program rather than a hope about model behaviour. The only thing
> that leaves an agent is a masked verdict, which never names which constraint was crossed and never
> exposes the sheet, so the coordinator is untrusted by construction. Among options feasible for
> everyone, Parley lifts the least-happy participant and breaks ties on total welfare. When no
> option is feasible for all, it returns an honest deadlock instead of a forced bad decision.
> Every run emits a tamper-evident transcript that each owner verifies locally against their own
> sheet, revealing nothing.

---

## 2. Fact sheet

| | |
|---|---|
| Name | Parley (lowercase "parley" in the wordmark, capitalised in prose) |
| Category | Infrastructure for multi-agent systems; agent governance and coordination |
| Founded | 2026 |
| Headquarters | Valencia, Spain |
| Founder | Oleh Veheria, solo founder |
| Stage | Pre-seed, bootstrapped |
| Licence | Apache-2.0 (core) |
| Repository | github.com/5uper0/parley, public since 2026-07-18 |
| Live demo | parleyprotocol.com/demo/, runs in the browser, no signup |
| Runtime | Python 3.11 through 3.14 |
| Dependencies | None in the core, standard library only. Ed25519 signing is the one optional extra |
| Tests | 181 passing, including a red-team suite for preference-extraction attacks |
| External contributors | 1 merged pull request from outside the project |
| Self-hosting | `docker run` one-liner; nothing calls home |
| Business model | Open core. The consensus engine is Apache-2.0; the hosted broker is commercial |

---

## 3. The problem, in the words we actually use

Standards such as MCP and A2A settled the transport question: agents can now discover each other and
exchange messages. They deliberately did not settle the adversarial question. If your agent and my
agent are negotiating a delivery window, a contract clause or a shared budget, both of us are trusting
a language model to hold a line it was merely told to hold. There is no artifact afterwards that
proves it did.

Three failure modes follow, and Parley closes each one in code:

1. **A model can be talked out of a constraint.** Parley makes hard constraints executable
   predicates that reject an option. Persuasion has no surface to work on.
2. **A coordinator sees everyone's cards.** Parley's agents emit a masked verdict only. The
   coordinator learns whether an option is acceptable, never why, and never the sheet.
3. **Nobody can audit the outcome.** Parley emits a hash-chained transcript of the masked verdicts.
   Each owner replays it against their own private sheet and confirms no red line of theirs was
   crossed, without revealing the sheet to anyone.

**What we deliberately do not claim.** Non-betrayal is provable with respect to the red lines an owner
actually encoded. Parley does not read minds, does not judge whether a sheet captures what someone
meant, and does not make a language model honest. It makes the boundary the owner wrote enforceable
and the result checkable.

---

## 4. Why now

Three things landed within roughly a year of each other: agents that can take real actions on
someone's behalf, a standard transport for agent-to-agent contact, and organisations willing to put
those agents in front of counterparties. The referee layer is the piece that did not arrive with
them. The comparable moment is payments before settlement rails, where the messaging worked long
before anyone could prove what had been agreed.

---

## 5. What makes it different

| | Parley | Single-owner orchestration (AutoGen, CrewAI) | On-chain agent commerce (Fetch.ai, Olas) |
|---|---|---|---|
| Whose interests | Several rival owners | One principal, many workers | Two counterparties |
| Parties per decision | N, multilateral | N workers, one goal | Typically bilateral |
| Trust anchor | Code predicates and a local replay | The orchestrator | A chain and a token |
| Crypto required | No | No | Yes |
| Deployment | Self-hosted, no external calls | Self-hosted or SaaS | Public network |

---

## 6. Founder

**Oleh Veheria**, founder. Valencia, Spain. Ukrainian.

A decade building systems where the interesting failures were about conflicting incentives rather
than uptime. Parley started from a practical annoyance: every agent framework assumed the agents
were on the same side, and the moment they were not, the design had nothing to say.

Contact: oleh@veheria.tech · LinkedIn: linkedin.com/in/oleh-veheria · GitHub: github.com/5uper0

---

## 7. Quotes, cleared for use

> "Every agent framework assumes the agents are on the same side. Parley is what you need for the
> hour when they are not."

> "A red line that a model can be argued out of is not a red line. It is a suggestion with good
> manners."

> "The coordinator should not need to be trusted. In Parley it does not learn enough to be worth
> corrupting."

> "The point is not that the decision is good. The point is that afterwards you can check it
> yourself, without showing anyone your cards."

---

## 8. Assets

All assets live in the repository under `docs/brand/assets/` and are cleared for editorial use.

| Asset | File | Use |
|---|---|---|
| Open Graph card | `og-card.png` | Article header, link preview |
| Proof card | `proofcard.png` | Illustrating the verifiable transcript |
| Motion clip | `parley-money-shot.gif` | A decision resolving end to end |
| Favicon set | `favicon/` | Small placements |

**Colour, for anyone laying out a page.** Parley indigo `#3A45B0` is the engine. Verify green
`#0E8F63` is a proven verdict. Red-line red `#C42121` marks a deterministic block and is never
decorative. Masked amber `#B87C15` is a hidden verdict. Typefaces are Inter for text and JetBrains
Mono for anything that represents a receipt, a hash or a signature.

**Naming.** Write "Parley" in prose. The wordmark is lowercase. It is not "Parley Protocol",
not "ParleyAI", and there is no space or hyphen variant. The domain is parleyprotocol.com because
parley.com was taken, which is the whole story behind it.

---

## 9. Questions we get, answered

**Is this a blockchain project?**
No, and deliberately so. Verification is a local replay of a hash-chained record against your own
private data. There is no chain, no token and no network to join.

**What stops the coordinator from cheating?**
Structurally, it never learns enough to cheat usefully: it sees a masked verdict, never the reason
and never the sheet. On top of that, `verify_outcome` lets anyone replay the public record and
confirm the announced decision really is the max-min one, so a coordinator cannot quietly finalise
some other feasible option.

What signing does **not** yet do, and we would rather say so than be caught saying otherwise: an
Ed25519 signature binds a key to an exact option and verdict pair, which stops a signed verdict
being altered or moved to another option, but it does not prove *who* signed. There is no trusted
owner-to-key roster yet, so a coordinator holding any key could sign a fabricated verdict under its
own key, and a genuine signed verdict carries no nonce, so it can be replayed into another parley
that reuses the same option. Today the guarantee is tamper-evidence, not authenticity. The roster
pin and replay binding are the v0.2 work, and both limits are listed in `SECURITY.md`.

**What happens when there is no acceptable option?**
Parley returns a deadlock and says so. Forcing an agreement that crosses somebody's red line is the
outcome the whole design exists to prevent.

**Who is it for today?**
Teams putting agents in front of a counterparty where the wrong answer is expensive and someone will
later ask how the decision was reached. Compliance-adjacent operations were the first cluster we
looked at.

**How much of it is real?**
The consensus engine, the masking, the signed transcript and the networked mode where each bot is its
own process are all in the repository with tests. The commercial broker is not built yet.

**Is it usable without writing Python?**
The demo runs in a browser with no signup. Integration today is a Python API or an HTTP endpoint per
agent.

---

## 10. Contact

Press and partnerships: oleh@veheria.tech
Response time: same day, European hours.
