# parley/net/identity.py — Spec

## Purpose
This module adds **Ed25519 cryptographic identity** to bots: signed Agent Cards and, more
importantly, signed verdicts. A signature binds a bot's key to the *exact* `(option, verdict)`
pair, so a coordinator that assembles the transcript can neither **forge** a verdict nor
**replay** a real one against a different option. That upgrades the transcript from merely
tamper-evident (any edit changes the hash) to **audit-grade / authentic** (each signed
verdict provably came from its owner for its option). It is an **optional** layer — the
zero-dependency core never imports it.

## The zero-dependency boundary (explicit)

- **This is the only module in `parley/` that imports `pynacl`** (`nacl.signing`,
  `nacl.encoding`, `nacl.exceptions`). It lives behind the optional `crypto` extra in
  `pyproject.toml` (`crypto = ["pynacl>=1.5"]`; `dev` also pulls it in). `pip install parley`
  with no extras never installs pynacl and never imports this file.
- **The core carries signatures as plain data, not crypto.** `Verdict.sig` and
  `Verdict.pubkey_hex` are `Optional[str]` fields on the stdlib `agent.Verdict`; `transcript.py`
  stores them as strings and computes only SHA-256 (stdlib `hashlib`). No core module calls
  into nacl. Signing/verifying is entirely opt-in and isolated here.
- **Consumers guard the import.** Tests do `pytest.importorskip("nacl")`; callers that want
  verification import `parley.net.identity` lazily. If the extra is absent, the core still
  runs — verdicts simply carry `sig=None`/`pubkey_hex=None` and `verify_transcript` skips
  them.

## Public API

- `verdict_payload(option, owner, acceptable, score, reason) -> bytes`
  — the canonical bytes a bot signs for one verdict:
  `json.dumps({"owner","option","acceptable","score","reason"}, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")`.
  Binds owner + option + full verdict content.
- `@dataclass(frozen=True) AgentCard(owner: str, pubkey_hex: str, protocol: str = "parley/0.1")`
  — public discovery identity (no private key, no sheet).
  - `.verify(message: bytes, sig_hex: str) -> bool` — `True` iff the signature validates;
    catches `BadSignatureError`/`ValueError` and returns `False`.
  - `.to_dict()` / `.from_dict(d)`.
- `class Identity.__init__(self, owner: str, signing_key: SigningKey)` — a bot's secret identity.
  - `classmethod generate(owner) -> Identity` — fresh Ed25519 keypair.
  - `.card() -> AgentCard` — the public card (hex-encoded verify key).
  - `.sign(message: bytes) -> str` — hex signature over arbitrary bytes.
  - `.sign_verdict(option, verdict) -> str` — sign `verdict_payload(...)` for this verdict.
- `verify_transcript(transcript) -> bool`
  — every **signed** verdict must validate against its own `pubkey_hex` for its own `option`;
  unsigned (local) verdicts are skipped. `False` if any signed verdict fails.

## Data model

- **`AgentCard`** (frozen): `owner`, `pubkey_hex` (64-char hex Ed25519 verify key),
  `protocol` (default `"parley/0.1"`). Public only — never carries the signing key.
- **`Identity`**: `owner` + private `_sk: SigningKey` (never serialized, never exposed).
- **verdict payload**: a canonical JSON object over exactly the five fields that must be
  bound — `owner`, `option`, `acceptable`, `score`, `reason`. `sig`/`pubkey_hex` are *not* in
  the payload (a signature can't sign itself).

## Invariants (must never break)

- **A signature binds the whole verdict to its option.** `verdict_payload` includes `option`
  plus `acceptable`/`score`/`reason`, so moving a verdict to another option or flipping any of
  those fields invalidates the signature. This is what stops a coordinator lying about who
  agreed to what. (`test_signed_verdict_is_bound_to_its_option_and_content`.)
- **Canonicalization matches the core.** `sort_keys=True` + `ensure_ascii=False` +
  `default=str` mirror `transcript.hash()` so the bytes a bot signs equal the bytes
  `verify_transcript` reconstructs from the recorded entry. Diverging the json flags would
  silently break every signature check.
- **The private key never leaves the bot.** `Identity._sk` is not in any `to_dict`/card;
  only the verify key (as `pubkey_hex`) is ever published. (`test_card_exposes_owner_and_pubkey_only`.)
- **One key cannot forge for another owner.** Verification is against the card's own
  `pubkey_hex`, so a signature from key A fails on key B's card.
  (`test_a_key_cannot_forge_for_another`.)
- **Verification fails closed.** `AgentCard.verify` returns `False` (never raises) on a bad
  signature or malformed hex, so a single tampered verdict makes `verify_transcript` return
  `False` rather than crashing.
- **Unsigned verdicts are skipped, not rejected.** `verify_transcript` `continue`s past any
  verdict lacking `sig` or `pubkey_hex`, so mixed local/remote parleys verify the signed
  subset without penalizing local (unsigned) agents — the core stays usable without crypto.

## Interactions

- **`agent.py`**: `Verdict.sig`/`pubkey_hex` are the transport fields these signatures ride in;
  `sign_verdict` reads `verdict.owner/acceptable/score/reason`.
- **`net/bot.py` / `net/client.py`**: a signing bot fills `sig`/`pubkey_hex` on its `Verdict`
  before it goes over the wire (`POST /consider`); `AgentCard` backs `GET /card` discovery.
- **`transcript.py`**: `verify_transcript` iterates `transcript.entries[*]["verdicts"]`,
  rebuilds `verdict_payload(entry["option"], v["owner"], v["acceptable"], v["score"], v["reason"])`,
  and checks it against an `AgentCard(v["owner"], v["pubkey_hex"])`. The stored `sig`/`pubkey_hex`
  are exactly what the transcript records.
- **Data crossing the boundary**: public `AgentCard` (owner + verify key) and hex signature
  strings. The signing key and the private sheet never cross.

## Failure modes / edge cases

- **Bad/tampered signature or malformed hex**: `verify` catches `BadSignatureError`/`ValueError`
  → `False` (`test_sign_verify_roundtrip_and_tamper`).
- **Coordinator flips a recorded field**: rebuilt payload no longer matches the signature →
  `verify_transcript` returns `False` (`test_signed_transcript_detects_coordinator_forgery`
  flips `acceptable`).
- **Verdict missing `sig` or `pubkey_hex`**: skipped by `verify_transcript` (treated as an
  unsigned local verdict).
- **pynacl not installed**: importing this module raises `ImportError`; the core and unsigned
  parleys are unaffected because nothing in the core imports it (tests `importorskip`).
- **No handling for key rotation / revocation**: a card is trusted purely by its `pubkey_hex`;
  there is no registry, expiry, or revocation check here — out of scope for this layer.

## Test coverage

`tests/test_identity.py` (guarded by `pytest.importorskip("nacl")`):
- `test_card_exposes_owner_and_pubkey_only` — card carries owner + 64-hex pubkey, nothing else.
- `test_sign_verify_roundtrip_and_tamper` — valid sig verifies; tampered message fails.
- `test_a_key_cannot_forge_for_another` — Ana's signature fails on Bob's card.
- `test_signed_verdict_is_bound_to_its_option_and_content` — signature bound to the exact
  option and to `acceptable`/`score`/`reason`; changing any one fails verification.

`tests/test_net.py`:
- `test_signed_transcript_detects_coordinator_forgery` — end-to-end over HTTP: `verify_transcript`
  is `True` for an honest record and `False` after a coordinator flips a recorded verdict.

## Open questions / roadmap
- **Identity/trust registry.** `docs/ROADMAP.md`'s money thesis names a "verified identities"
  / trust-registry as a paid layer; today a card is self-asserted with no rotation, expiry, or
  revocation.
- **Binding the whole transcript, not just per-verdict.** Signatures authenticate individual
  verdicts; there is no single coordinator-level signature/anchor over the final `hash()` +
  decision.
- **A2A transport.** The `protocol = "parley/0.1"` tag anticipates a wire protocol; the CLAUDE.md
  seam notes A2A transport drops in at the `RemoteAgent` boundary next.
