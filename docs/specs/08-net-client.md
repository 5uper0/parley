# parley/net/client.py — Spec

## Purpose
`RemoteAgent` is the client half of the seam: it speaks the bot's HTTP protocol but exposes
the **exact same `.owner` / `.consider(option) -> Verdict` interface as a local `Agent`**, so
`run_consensus` cannot tell a remote bot from an in-process one. That indistinguishability is
deliberate — it is where A2A transport and LLM-elicited sheets drop in without touching the
consensus core. It also carries the bot's signature and pubkey off the wire back into the
`Verdict`, so the transcript stays verifiable end to end.

## Public API

- `class RemoteAgent(url, token=None, timeout=5)`
  — On construction, normalizes `url` (strips trailing `/`), then does discovery: `GET /card`
  and sets `self.owner = card["owner"]` and `self.pubkey_hex = card.get("pubkey_hex")`
  (`None` for an unsigned bot). Holds `token` and `timeout` for later calls.
- `RemoteAgent.owner: str` — the delegate's owner name (same attribute a local `Agent` exposes).
- `RemoteAgent.consider(self, option) -> Verdict`
  — `POST /consider` with `{"option": option}`; reconstructs and returns a
  `parley.agent.Verdict` from the response, including `sig`/`pubkey_hex` when present. Same
  signature and return type as `Agent.consider`.
- `discover(urls, token=None) -> list[RemoteAgent]`
  — Fetch each bot's Agent Card and return connected `RemoteAgent`s (one per URL, in order).
- `RemoteAgent.pubkey_hex: Optional[str]` — the bot's public key from its card (or `None`).

## Data model

- **Outbound request:** `{"option": option}`, JSON-encoded UTF-8, sent to `<url>/consider`.
- **Headers (`_headers`):** always `Content-Type: application/json`; adds
  `Authorization: Bearer <token>` when `token` is set. Used for both GET and POST.
- **Verdict reconstruction:** from the response dict `d`, builds
  `Verdict(owner=d["owner"], acceptable=d["acceptable"], score=d["score"],
  reason=d["reason"], sig=d.get("sig"), pubkey_hex=d.get("pubkey_hex"))`. `sig`/`pubkey_hex`
  default to `None`, so an unsigned bot yields an unsigned (but valid) `Verdict`.
- **Card:** consumed only for `owner` + optional `pubkey_hex`; nothing else is read.

## Invariants (must never break)

- **Local/remote indistinguishability.** `RemoteAgent` implements exactly `.owner` (attr) and
  `.consider(option) -> Verdict` (method) — the same duck-typed interface `run_consensus`
  calls on a local `Agent`. No consensus code branches on transport. (`test_net.py` runs the
  identical `run_consensus(agents, OPTIONS)` over `RemoteAgent`s and reaches the same
  outcome; CLAUDE.md pins this seam.)
- **Signatures survive the round trip.** `consider` copies `sig` and `pubkey_hex` off the wire
  into the returned `Verdict`, so they flow into the transcript and `verify_transcript()`
  still works over HTTP. (`test_signed_transcript_detects_coordinator_forgery`.)
- **The client never learns the sheet.** It only ever sees the card (owner + pubkey) and the
  masked verdict — there is no code path that requests or receives constraints.
- **Return type is the core `Verdict`.** `consider` always returns a `parley.agent.Verdict`
  (never a raw dict), keeping remote agents type-compatible with the core.

## Interactions

- **Talks to** `parley.net.bot`'s HTTP server (`/card`, `/consider`) via `urllib.request`.
- **Returns** `parley.agent.Verdict` — the only type crossing back into the core.
- **Consumed by** `parley.consensus.run_consensus`, which treats it identically to a local
  `Agent`; and by `examples/run_env.py` (via `discover`) after each bot process is up.
- **Data crossing the boundary:** outbound = `{"option": ...}` + optional bearer; inbound =
  the card dict (owner, pubkey) and the verdict dict (masked verdict + optional signature).

## Failure modes / edge cases

- **Bot unreachable / discovery fails:** `__init__` calls `_get("/card")` eagerly, so a dead
  or not-yet-up bot raises `urllib.error.URLError`/`HTTPError` at construction. `run_env.py`
  guards this with `_wait_up()` before `discover`.
- **HTTP error status (401/413/429/400/404):** surfaces as `urllib.error.HTTPError` from
  `urlopen` — not swallowed. A missing/invalid token yields 401 on `/consider`; enforcement
  lives in the bot, the client just carries the header.
- **Timeout:** every request uses `timeout` (default 5 s) → `socket.timeout` on a hung bot.
  Note `discover` does **not** thread `timeout` through, so discovered agents use the default 5 s.
- **Unsigned bot:** `pubkey_hex` is `None` and `consider` returns a `Verdict` with
  `sig=None`/`pubkey_hex=None` — valid, just skipped by `verify_transcript`.
- **Malformed response:** missing required keys (`owner`/`acceptable`/`score`/`reason`) raise
  `KeyError`; the client trusts a well-behaved bot for the response shape (only `sig`/`pubkey_hex`
  are optional via `.get`).

## Test coverage

`tests/test_net.py` (all via real `serve()` bots on ephemeral ports):
- `test_two_bots_reach_consensus_over_http` — `[RemoteAgent(u) for u in urls]`, asserts
  `[a.owner for a in agents] == ["Ana", "Bob"]` (discovery), then `run_consensus` → `agreed`
  and per-owner `verify_non_betrayal`.
- `test_five_bots_reach_consensus_over_http` — five `RemoteAgent`s reach consensus; every
  owner's local sheet confirms non-betrayal.
- `test_wire_never_carries_the_private_sheet` — after a full remote parley, no constraint name
  appears in the transcript (client never pulls the sheet).
- `test_signed_transcript_detects_coordinator_forgery` — signatures reconstructed by
  `consider` make `verify_transcript` pass, and a flipped verdict makes it fail.

## Open questions / roadmap
- **A2A transport.** The `.owner`/`.consider` seam is exactly where an agent-to-agent
  transport replaces plain HTTP without touching `run_consensus`. (CLAUDE.md.)
- **Multi-round counter-proposals (Exp 1).** `docs/ROADMAP.md` plans negotiation beyond
  scoring fixed options; that will extend the client's interaction pattern (more than one
  `consider` round), while keeping the local/remote seam intact.
- **Response-shape hardening / retries.** No retry, backoff, or strict response validation
  today — acceptable for trusted in-process bots and `cloudflared`-fronted demos.
