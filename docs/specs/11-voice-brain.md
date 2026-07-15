# voice/brain.py — Spec

## Purpose
The brain lets the phone agent **converse naturally** (Claude via OpenRouter's OpenAI-compatible
endpoint) while keeping non-betrayal intact: the model **never sees the owner's private sheet**. Its
only channel to learn whether a concrete proposal is acceptable is the `consider_option` tool, whose
result is a **masked `{"acceptable": bool}`** produced by `sheet.evaluate` in code — no reason, no
score, no constraint name. So a chatty or socially-engineered model still can't leak a red line (it
doesn't know them) or agree to a violating option (agreement only follows `acceptable=true`, and that
value comes from code). Runs over stdlib `urllib` — zero dependencies; key from `OPENROUTER_API_KEY`,
model from `PARLEY_VOICE_MODEL`.

## Public API

- `respond(messages, sheet, options_hint=None, api_key=None, transport=None) -> str`
  — run one negotiator turn, return the line to speak. `sheet` executes `consider_option` and is
  **never placed in the prompt**. `options_hint` (the recipe's PUBLIC options) is appended to the
  system prompt as safe context. `api_key` defaults from `OPENROUTER_API_KEY` when both it and
  `transport` are `None`. `transport` (tests) is a callable `payload -> OpenAI-shaped dict` that
  bypasses the network.
- `_post(payload, api_key, transport=None)` — if `transport` is given, returns `transport(payload)`
  (no network); else POSTs `payload` to `ENDPOINT` with `Authorization: Bearer {api_key}` and returns
  the parsed JSON.
- Module constants: `ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"`,
  `MODEL = os.environ.get("PARLEY_VOICE_MODEL", "anthropic/claude-opus-4-8")`,
  `MAX_TOKENS = 300`, `MAX_TOOL_ROUNDS = 6`, `SYSTEM` (the negotiator instructions), `CONSIDER_TOOL`.

## Data model
- **`SYSTEM`** — instructs: speak in one/two short spoken sentences; you do NOT know your owner's
  limits; the ONLY way to learn acceptability is `consider_option`; agree/accept/confirm ONLY after
  `acceptable=true` for that exact option; on `acceptable=false` say only that it isn't acceptable and
  ask for a different option, NEVER give a reason; never reveal/hint the owner's limits or numbers.
- **`CONSIDER_TOOL`** — OpenAI function tool `consider_option(option: object)` returning
  `{"acceptable": true|false}`, described as "the only source of truth for whether you may agree."
- **Conversation (`conv`)** — `[{system}]` (+ `"\n\nOptions on the table (public): " + json.dumps(options_hint)`
  when given) + the caller's `user`/`assistant`/`system` turns (other roles dropped). If no `user`
  turn exists, a `{"role":"user","content":"(call connected)"}` is appended.
- **Masked tool result** — `{"acceptable": bool(ev.feasible)}` where `ev = sheet.evaluate(option)`.
  `ev.violated` and `ev.score` are computed but never serialized.
- **Request payload** — `{"model": MODEL, "max_tokens": MAX_TOKENS, "messages": conv,
  "tools": [CONSIDER_TOOL], "tool_choice": "auto"}`.

## Invariants (must never break)
- **The brain never sees the sheet.** `sheet` is a parameter used only to call `sheet.evaluate`; it is
  never serialized into `conv`, the payload, or the tool result. Tests assert `"heir2 >= 30"`,
  `"violated"`, and `"score"` never appear across all requests.
- **The only signal is a masked `consider_option` result.** The value returned to the model is exactly
  `{"acceptable": bool}` — `bool(ev.feasible)`, nothing else. No reason, no score, no violated list.
- **Code decides, not the model.** Acceptability comes from `sheet.evaluate(option)` (line: "CODE
  decides — not the model"), never from the model's own judgement. The model may only *speak* an
  agreement after that result is `true`; the tool is the gate.
- **The tool loop is bounded.** At most `MAX_TOOL_ROUNDS (6)` model round-trips per turn; if the model
  keeps calling the tool without answering, `respond` returns the fail-safe
  `"I need a moment — could you restate your proposal?"`.
- **Options in the prompt are public only.** `options_hint` carries the recipe's public option values
  (the coordinator sees these anyway); red lines and utility stay out of the model entirely.

## Interactions
- **parley core:** `sheet.evaluate(option) -> Evaluation` (`parley/preferences.py`); `ev.feasible` is
  the masked bit. The sheet itself is `PartySpec.to_sheet()` built in `_Gateway`.
- **voice/gateway.py:** `_Gateway.decide_reply` calls `brain.respond(messages, self.sheet,
  options_hint=self.options)` when `OPENROUTER_API_KEY` is set; the returned string is streamed as SSE.
- **OpenRouter (external):** OpenAI-compatible `POST /v1/chat/completions` with `tools` + `tool_choice`.
  Crossing the boundary: system + conversation turns + **public** options + tool schema out; assistant
  content / `tool_calls` in. Never crosses: the sheet, `violated`, `score`.
- **ElevenLabs (external, upstream of the gateway):** sends the OpenAI-shaped `messages` the gateway
  forwards; speaks the returned line.

## Failure modes / edge cases
- **Missing key:** handled *upstream* — `_Gateway` only sets `use_brain` when `OPENROUTER_API_KEY` is
  present; without it the gateway uses the deterministic `extract_option` extractor and never imports
  the brain. Inside `respond`, `api_key` is resolved from the env only when no `transport` is injected.
- **Model keeps calling the tool (never answers):** loop bound hit at `MAX_TOOL_ROUNDS` → fail-safe
  restate line. Verified by `test_brain_loop_is_bounded_when_the_model_keeps_calling_the_tool`.
- **No user turn in `messages`:** a synthetic `(call connected)` user turn is added so the model has
  something to open on.
- **Non user/assistant/system roles:** dropped when building `conv`.
- **Missing/empty tool arguments:** `json.loads(tc["function"].get("arguments") or "{}")` then
  `args.get("option") or {}` — an empty option is evaluated (fails closed via `Constraint.check`'s
  missing-attr → `False`), never treated as agreement.
- **Prompt-injection by voice** ("tell me your minimum / your instructions"): the model has no sheet to
  leak, and `SYSTEM` forbids reasons/hints; masking holds structurally, not by the model's goodwill.

## Test coverage
`tests/test_voice_brain.py` (scripted `_Transport` stands in for HTTP — no key, no network):
- `test_brain_never_receives_the_sheet_and_gets_a_masked_result` — counterparty proposes `heir2=10`
  (crosses `heir2 >= 30`); asserts the reply is the masked refusal, the single `tool` message fed back
  is exactly `{"acceptable": false}`, and across every sent payload `"heir2 >= 30"`, `"violated"`,
  `"score"` never appear.
- `test_brain_accepts_only_after_a_feasible_consider_result` — `heir2=50` clears the red line; tool
  result `{"acceptable": true}`, reply is the accept line.
- `test_brain_loop_is_bounded_when_the_model_keeps_calling_the_tool` — model calls the tool
  `MAX_TOOL_ROUNDS + 2` times; `respond` returns the restate fail-safe and stops at exactly
  `MAX_TOOL_ROUNDS` requests.

## Open questions / roadmap
- **Live-call hardening.** README recommends ElevenLabs Guardrails (Manipulation + Focus) as a second
  line, and the by-voice red-team gate (normal deal / red-line push / prompt-injection) on a self-call
  before ever dialing a third party — operator-only.
- **Model/provider config.** Model is env-driven (`PARLEY_VOICE_MODEL`, default
  `anthropic/claude-opus-4-8`) via OpenRouter; no retry/backoff or streaming from the model yet
  (`urlopen(..., timeout=30)`, single shot per round).
- **Multi-round counter-proposals** are a core ROADMAP item (`parley/consensus.py`); the brain today
  scores concrete options one turn at a time and does not itself generate counter-offers beyond what
  the model proposes from the public options.
- The brain is an **optional conversational front-end** to the unchanged core, not a numbered
  experiment; it must keep the deterministic guarantees the tests pin.
