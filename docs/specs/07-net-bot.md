# parley/net/bot.py — Spec

## Purpose
This module turns a local `Agent` into a network peer: a hardened HTTP server that
publishes a sheet-free Agent Card and answers `/consider` with an Ed25519-**signed**,
**masked** `Verdict`. It is the trust boundary of the networked system — the coordinator
that assembles the transcript is untrusted by construction, so the server must never leak
the private sheet and must survive a hostile client (the preference-extraction and DoS
attacks reconstructed in the red-team baseline). Everything the server exposes is safe to
show an adversary; the private constraints stay inside the process.

## Public API

- `serve(owner, sheet, host="127.0.0.1", port=0, identity="auto", auth_token=None, rate_limit=None) -> ThreadingHTTPServer`
  — Build (do **not** run) a bot server around `Agent(owner, sheet)`. `identity="auto"`
  generates a fresh `Identity` (signing key); `port=0` binds an ephemeral port. Returns the
  `ThreadingHTTPServer`; caller runs `.serve_forever()` (or `.shutdown()`). The returned
  server's bound port is read from `httpd.server_address[1]`.
- `main()` — CLI entrypoint (`python -m parley.net.bot --profile <name> --port <n> [--host H]`).
  Loads a sheet from `PROFILES`, reads `PARLEY_TOKEN` from the env (auth on iff set), and
  runs `serve_forever()`. **Rate limit is not wired to the CLI** — a standalone bot has no
  throttling unless started via `serve(..., rate_limit=...)` in-process.
- `MAX_BODY = 4096` — hard byte cap on a `/consider` request body.
- `_RateLimiter(spec)` / `_make_handler(...)` — internal (leading underscore); not API.

### HTTP endpoints

| Method | Path        | Auth | Request body                | Success response |
|--------|-------------|------|-----------------------------|------------------|
| GET    | `/card`     | none | —                           | `200` `{"owner", "protocol":"parley/0.1"[, "pubkey_hex"]}` |
| POST   | `/consider` | bearer (if `auth_token` set) | `{"option": <object>}` | `200` `{"owner","acceptable","score","reason"[, "sig","pubkey_hex"]}` |

- `/card` is discovery only: owner + protocol tag, plus `pubkey_hex` when an identity exists.
  It carries **no sheet, no constraint names, no options**.
- `/consider` maps `data["option"]` → `agent.consider(option)` → masked `Verdict`, and (when
  an identity exists) attaches `sig = identity.sign_verdict(option, v)` and the bot's
  `pubkey_hex`. Any other method/path → `404 {"error":"not found"}`.

## Data model

- **Card wire form:** `{"owner": str, "protocol": "parley/0.1", "pubkey_hex"?: str}`.
- **Consider request:** `{"option": <JSON object>}` — `option` must be a `dict`.
- **Consider response (verdict wire form):** `{"owner": str, "acceptable": bool, "score":
  float, "reason": "ok"|"red-line", "sig"?: hex str, "pubkey_hex"?: hex str}`. This is the
  exact field set `RemoteAgent` reconstructs into a `Verdict`. `reason` is masked — it never
  names the crossed constraint.
- **Signature payload:** `sig` covers `verdict_payload(option, owner, acceptable, score,
  reason)` (canonical `sort_keys` JSON, from `identity.py`) — it binds the signature to the
  exact option **and** the verdict content.
- **Rate-limiter state:** `_RateLimiter` keeps a fixed-window `{client_ip: (count, start)}`
  under a lock; `spec` is `(max, window_seconds)`, and a falsy `max` disables it (`allow`
  returns `True`).

## Invariants (must never break)

- **The sheet never crosses the wire.** The server returns only a masked `Verdict`
  (`acceptable` + `score` + `"ok"/"red-line"`). It never emits `violated`, constraint names,
  the utility, or the option set. Enforced by `Agent.consider` producing the masked verdict
  and by `/card` carrying no sheet. (`test_wire_never_carries_the_private_sheet` asserts none
  of the five constraint names appear anywhere in the transcript.)
- **Signatures ride through to the transcript.** When an identity exists, every `/consider`
  response is signed over its specific option; the signature and pubkey flow via the wire →
  `RemoteAgent` → `Verdict` → `Transcript`, so `verify_transcript()` can later prove no verdict
  was forged or moved. (`test_signed_transcript_detects_coordinator_forgery`.)
- **Reason stays masked.** `reason` is only ever `"ok"` or `"red-line"`, produced upstream in
  `Agent.consider`; the server passes it through verbatim and adds nothing.
- **Every failure is a fixed 4xx, never a 500/crash/unbounded read.** Body is capped before
  reading (`length > MAX_BODY` → 413 before `rfile.read`); bad JSON / missing `option` /
  non-dict `option` / predicate raising are caught and mapped to 400. (`test_redteam.py`.)
- **Auth and rate-limit fail closed when configured.** No/incorrect bearer → 401 before any
  work; over-limit → 429 before body read.

## Interactions

- **Wraps** `parley.agent.Agent` (calls `.owner` and `.consider(option)`), producing a
  `parley.agent.Verdict`.
- **Signs with** `parley.net.identity.Identity` (`.card().pubkey_hex`, `.sign_verdict`).
- **Fed by** `parley.net.profiles.PROFILES` in `main()` (CLI) and in every test/example.
- **Consumed by** `parley.net.client.RemoteAgent` over HTTP; that client is what the
  consensus core (`run_consensus`) actually holds. Data crossing the boundary is exactly the
  card dict and the verdict dict above — Verdict + optional signature, never the sheet.
- **Launched as a separate OS process** by `examples/run_env.py` via `python -m parley.net.bot`.

## Failure modes / edge cases

- **Wrong path / method:** `404 {"error":"not found"}` (any non-`/card` GET, any non-`/consider` POST).
- **Missing/invalid bearer (auth on):** `401 {"error":"unauthorized"}` before rate-limit or
  body read. Exact check: `Authorization == f"Bearer {auth_token}"`. Auth off ⇒ always allowed.
- **Over rate limit:** `429 {"error":"rate limited"}` — fixed window per client IP
  (`self.client_address[0]`); the window resets after `window` seconds.
- **Body larger than `MAX_BODY` (4096 B):** `413 {"error":"payload too large"}`, decided from
  the `Content-Length` header *before* reading the socket (bounds the read).
- **Malformed body:** missing `option` key (`KeyError`), non-dict `option` (`ValueError`),
  invalid JSON (`json.JSONDecodeError`), or a predicate that raises on a malformed option
  (`KeyError`/`TypeError`/`ValueError`) → `400 {"error":"invalid option"}`. Empty body reads
  as `{}` then fails the missing-`option` path → 400.
- **`identity=None` passed to `serve`:** server still answers, but `/card` omits `pubkey_hex`
  and `/consider` omits `sig`/`pubkey_hex` — verdicts are then unsigned (skipped by
  `verify_transcript`). Default `identity="auto"` means signatures are on by default.
- **CLI standalone has no rate limit** (see Public API) — a hole only relevant when a bot is
  exposed directly rather than via in-process `serve`.

## Test coverage

- `tests/test_net.py`
  - `test_two_bots_reach_consensus_over_http` / `test_five_bots_reach_consensus_over_http` —
    real `serve()` bots on ephemeral ports; consensus reached over HTTP; each owner replays
    their own sheet and `verify_non_betrayal` holds.
  - `test_wire_never_carries_the_private_sheet` — none of the constraint names leak into the
    transcript (the sheet-never-crosses invariant).
  - `test_signed_transcript_detects_coordinator_forgery` — `verify_transcript` is `True` for
    honest signed verdicts and `False` after a flipped `acceptable` (signatures ride through).
- `tests/test_redteam.py` (needs `nacl`)
  - `test_extraction_blocked_without_token` → 401.
  - `test_rate_limit_throttles_brute_force_probing` → 429 appears within 12 hits at `(5, 60)`.
  - `test_oversized_body_rejected` → 413 for a ~9 KB body.
  - `test_malformed_option_is_client_error_not_crash` → 400 for an option missing a needed key.

## Open questions / roadmap
- **A2A transport.** The card/verdict seam is the drop-in point for an agent-to-agent
  transport; today it is plain JSON over `http.server`. (CLAUDE.md "How the pieces connect".)
- **LLM-elicited sheets (Exp 1).** `parley/elicit.py` will produce the `PreferenceSheet` the
  bot serves; the server contract is unchanged — code still enforces, the LLM only authors
  the sheet. (`docs/ROADMAP.md`.)
- **CLI rate-limit / TLS.** `main()` exposes only `PARLEY_TOKEN`; wiring `rate_limit` and
  transport security to the CLI is unbuilt (fine while bots run in-process or behind
  `cloudflared`).
