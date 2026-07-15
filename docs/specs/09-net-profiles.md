# parley/net/profiles.py — Spec

## Purpose
This module is the demo fixture for the networked stack: five named personas, each a
**private** `PreferenceSheet` that lives inside its own bot process and is never sent on the
wire, plus one **public** agenda (`OPTIONS`) — the meeting slots everyone is trying to agree
on. It exists so the bot server, the client, `examples/run_env.py`, and the network tests all
share one concrete, conflicting-interest scenario without any of them hand-rolling sheets. It
carries no logic or guarantee of its own; it is data that exercises the guarantees enforced
elsewhere.

## Public API

- `OPTIONS: list[dict]` — the public agenda: eight `{"day": str, "hour": int}` meeting slots
  (`mon/tue/wed/thu/fri`, hours 9–17). This is the option set passed to `run_consensus`.
- `PROFILES: dict[str, Callable[[], PreferenceSheet]]` — maps a profile name to a **factory**
  (a zero-arg lambda) that builds a fresh `PreferenceSheet`. Keys: `"ana"`, `"bob"`, `"cara"`,
  `"dan"`, `"eve"`. Each call returns a new sheet (used both to serve a bot and, separately,
  to locally re-verify non-betrayal).

Consumers call it as: `PROFILES[name]()` to build a sheet, and `sorted(PROFILES)` /
`list(PROFILES)` for the CLI choices and iteration.

## Data model

Each factory returns `PreferenceSheet(owner, hard=[HardConstraint(name, predicate)],
utility=lambda o: float)`. The five personas encode deliberately conflicting interests:

| Profile | owner | hard red line (name → predicate: True = passes) | soft utility (1.0 preferred / else 0.5) |
|---------|-------|--------------------------------------------------|------------------------------------------|
| `ana`  | Ana  | `no-mornings` → `o["hour"] >= 11`  | `tue` |
| `bob`  | Bob  | `no-fridays` → `o["day"] != "fri"` | `hour == 15` |
| `cara` | Cara | `kids-pickup` → `o["hour"] <= 16`  | `wed` |
| `dan`  | Dan  | `no-mondays` → `o["day"] != "mon"` | `hour == 14` |
| `eve`  | Eve  | `afternoons-only` → `o["hour"] >= 13` | `thu` |

The constraint **names** (e.g. `no-mornings`) are the private strings that must never appear
on the wire — the network test asserts exactly this set stays out of the transcript. The
feasible-for-all-five intersection over `OPTIONS` is `{tue14, wed14, thu15}` (per `test_net`'s
comment), which is why the 5-bot scenario reaches consensus rather than deadlocking.

## Invariants (must never break)

- **Sheets are private; the agenda is public.** `OPTIONS` is shared plaintext; a
  `PreferenceSheet` only ever exists inside a bot process (or an owner's own re-verification)
  and is never serialized to the wire. The module's docstring states this contract.
- **Factories, not shared instances.** Each `PROFILES[name]` is a lambda so every consumer
  gets an independent sheet — the bot serves one, and the owner replays another locally for
  `verify_non_betrayal`. They must be equivalent but need not be the same object.
- **Constraint names stay off the wire.** The five names above are the leak canaries;
  `test_wire_never_carries_the_private_sheet` fails if any appears in the transcript. Changing
  a name here without updating that test would silently weaken the check.
- **Conflicting-but-satisfiable by design.** The personas conflict (mornings vs afternoons,
  Monday vs Friday, kids-pickup cap) yet leave a non-empty common-feasible set, so the demo
  proves *consensus*, not just deadlock. (A companion deadlock scenario lives elsewhere, not here.)

## Interactions

- **Imports** `PreferenceSheet` and `HardConstraint` from `parley.preferences`.
- **`parley/net/bot.py`** — `main()` uses `PROFILES[args.profile]()` to build the served
  sheet; `--profile` choices are `sorted(PROFILES)`.
- **`tests/test_net.py`, `tests/test_redteam.py`** — build bots from `PROFILES` and re-verify
  with fresh `PROFILES[p]()` sheets; iterate `OPTIONS`.
- **`examples/run_env.py`** — imports both `PROFILES` and `OPTIONS`; spawns one bot process per
  profile, runs consensus over `OPTIONS`, and re-verifies each owner locally.
- **Data crossing the boundary:** only `OPTIONS` (public) travels; the sheets do not. What
  comes back are masked `Verdict`s, never anything from a sheet.

## Failure modes / edge cases

- **Unknown profile key:** `PROFILES["nope"]` raises `KeyError`; the CLI constrains
  `--profile` to `sorted(PROFILES)` so `main()` can't hit it.
- **Predicate assumes option shape:** every predicate reads `o["hour"]` or `o["day"]`; an
  option missing those keys raises `KeyError` inside `sheet.evaluate` → the bot maps it to a
  400 (see `test_malformed_option_is_client_error_not_crash`). Well-formed `OPTIONS` never
  trip this.
- **Not a network payload:** this module must not grow serialization/transport code — it is
  pure demo data. Any masking/verification logic belongs in `agent.py` / `transcript.py`.

## Test coverage
- `tests/test_net.py` — `PROFILES`/`OPTIONS` drive all four network tests (2-bot and 5-bot
  consensus, sheet-never-leaks, signed-forgery-detection).
- `tests/test_redteam.py` — `_start` builds every hardened-bot fixture from `PROFILES["ana"]()`.
- Consumed indirectly wherever the networked scenario is exercised; the module has no
  dedicated test of its own (it is fixtures, not logic).

## Open questions / roadmap
- **Real, non-demo sheets.** These are toy meeting-scheduling personas. `docs/ROADMAP.md` Exp 1
  moves to real group decisions and NL-elicited sheets (`parley/elicit.py`), which will supply
  sheets from natural language rather than hand-written lambdas — this file stays as the
  canonical *demo* scenario.
- **Deadlock demo.** A companion no-common-feasible scenario would round out the personas
  (proving honest deadlock, not just agreement); not present in this module today.
- **Scenario breadth.** The KYC/procurement demo scenarios used by the public demo server live
  under `examples/demo/` (recipe JSON), separate from these scheduling personas.
