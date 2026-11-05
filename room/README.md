# room/

The browser side of the Parley Room. `engine.mjs` is a dependency-free JavaScript port of the Python
engine: a person's private sheet is applied to each option on their own device and only the masked
verdict (`acceptable`, `score`, `reason`) leaves it. `tests/golden/engine_vectors.json` freezes the
Python answers (regenerate with `scripts/gen-golden-vectors.py`); `node --test room/test/parity.test.mjs`
holds this engine to the same verdicts and the same transcript hash, byte for byte.

Limit: write whole numbers in options without a decimal point (`5`, not `5.0`), or the hash differs.
`relay/` is the Cloudflare relay: `core.mjs` (pure logic: key pin, session and nonce, signature check, max-min, record), `http.mjs`, `worker.mjs` (Durable Object per room), `wrangler.toml`. It sees an option list, public keys and signed masked verdicts, never a sheet. `node --test room/test/*.test.mjs` runs everything; `tests/test_room_relay_interop.py` proves a relay record verifies under Python's `verify_transcript`.
Status: engine and relay built, relay not deployed. The phone page is the next row in `docs/ROOM-ROADMAP.md`.

Deploy needs a secret first: `wrangler secret put LIMIT_SECRET` (any long random string; it keys the per-client room limit so addresses cannot be recovered from object names).
