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

Limits stated plainly: each person's link carries a secret token, so knowing a name is not enough to take a seat, but whoever creates the room sees every link and could still answer for someone. A phone checks the result against what it sent (hash, signatures, roster, max-min) and refuses to show one that does not match. The record names each owner next to each yes or no, so a room of two or three people can tell who blocked an option.
If a phone dies between taking its seat and saving its key, that seat cannot be recovered (`already-joined`); the organizer starts a new room.
Each person's link also carries a hash of the room's names, and the page itself carries the option list: a phone refuses a room whose names or options differ from those, so the relay cannot add a seat, drop one, or change what is being decided without the phone noticing.

What this does not give: the relay issues the seats and records the keys, so a dishonest relay could answer for someone else with a key of its own, or show two people two different records. Each person's own conditions still hold (an option they ruled out cannot be agreed), but the phone does not authenticate the other people. To catch two different records, compare the record code on each screen.

Seats: a link preview that only reads the page binds nothing; the seat is taken when the person presses the button. A second device with the same link is refused. The creator gets an `organizer_key` once, in the creation response, and can free a seat whose phone was lost (`POST /reissue`, before that person has submitted): the old link dies and the nonces change. The organizer screen for this is not built yet.
The creator already holds every link, so the creator can take any seat that has not submitted yet, with or without a reissue. A person's own phone notices (the send fails, or the result does not match what it sent), but the other phones and the record do not show it.
