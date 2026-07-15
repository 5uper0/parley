# Parley module specs

These specs are the **source of truth we build against** — one per module, each grounded in the
real code in this repo (not aspirational). A spec states what its module *guarantees*: the invariant
it holds, the interface it exposes, and the failure it refuses. When code and spec disagree, that is
a bug in one of them — reconcile, don't drift. Read the spec before touching the module.

## Core (`parley/`)

- [01-preferences](01-preferences.md) — the hard/soft split: red lines are code predicates that *reject* an option; soft utility only ranks options that already clear every red line.
- [02-agent](02-agent.md) — a delegate that masks: the only thing that leaves it is a `Verdict` (`acceptable`, `score`, reason `"ok"`/`"red-line"`), never the sheet, never which constraint was crossed.
- [03-consensus](03-consensus.md) — max-min group decision over options feasible for *everyone*: lift the least-happy participant, tie-broken by total welfare; no feasible option ⇒ honest deadlock.
- [04-transcript](04-transcript.md) — a tamper-evident SHA-256 record of public masked verdicts; each owner replays their own private sheet locally to prove non-betrayal without revealing it.
- [05-spec](05-spec.md) — declarative `DecisionSpec` recipes (constraints as shareable JSON data, never executable code) compiled into the unchanged engine.
- [06-net-identity](06-net-identity.md) — optional Ed25519 layer: a signature binds a bot's key to the exact `(option, verdict)` pair, making the transcript audit-grade — no forgery, no replay.

## Networking (`parley/net/`)

- [07-net-bot](07-net-bot.md) — each bot is its own OS process behind a hardened HTTP server: `GET /card` (discovery, no sheet) + `POST /consider` (signed verdict), with bearer auth, rate-limit, body cap, and input validation.
- [08-net-client](08-net-client.md) — `RemoteAgent` implements the identical `.owner`/`.consider()` interface, so `run_consensus` cannot tell local from remote; carries signature + pubkey into the `Verdict`.
- [09-net-profiles](09-net-profiles.md) — named private preference sheets (one per bot process) plus the shared public agenda of options everyone is trying to agree on.

## Voice (`voice/`)

- [10-voice-gateway](10-voice-gateway.md) — an OpenAI-compatible `/v1/chat/completions` (SSE) endpoint that registers Parley *as* the model: every spoken commitment first clears `sheet.evaluate` in code.
- [11-voice-brain](11-voice-brain.md) — the conversational LLM (Claude via OpenRouter) that speaks but never sees the sheet; its only channel to acceptability is a tool returning a masked `{"acceptable": bool}`.
- [12-voice-policy](12-voice-policy.md) — the speech-side of non-betrayal: the agent may only utter whitelisted, reason-free lines (accept / masked-refuse / fail-closed clarify), chosen by code from an `Evaluation`.

## Consumer MVP (planned, pre-code)

The implemented-module specs above describe current guarantees. The separate
[`mvp/`](mvp/README.md) package defines the complete consumer-facing product contract before any
implementation starts: 12 planned modules, their boundaries, privacy invariants, interfaces, and
acceptance criteria. Planned specs must not be presented as shipped capabilities.
