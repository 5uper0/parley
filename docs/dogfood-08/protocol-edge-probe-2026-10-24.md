# Protocol edge probe, 2026-10-24

Script: `docs/dogfood-08/probe_edges.py` (run from the repo root: `.venv/bin/python docs/dogfood-08/probe_edges.py`). It feeds 19 malformed or extreme specs to `parley.mcp.tool_decide`. Trigger: finding the `mcp` 2.x break while writing framework recipes; the owner asked to keep testing the protocol in different situations.

## Result

No crash and no wrong decision. Through the stdio server every exception comes back as `isError: true` with a readable text (verified: `parley-mcp` run with a bad `in` red line, JSON-RPC id 2). Red lines hold: when every option is infeasible the result is an honest deadlock; 60 parties are refused at the documented 50-party limit; 500 options work.

## Findings (all low severity; none touches a core property)

| # | Input | Behaviour | Why it matters | Suggested fix |
|---|---|---|---|---|
| 1 | two options with the same `id` | silent deadlock (`decision: null`), no error | a malformed spec reads as "no one could agree"; an honest deadlock is a real outcome, this is not | reject duplicate option ids with a clear error |
| 2 | `in` red line with a string value | raw Python `TypeError: 'in <string>' requires string as left operand` | message does not name the party or the attribute | validate `in`/`not_in` values are lists at spec load |
| 3 | string where a number is expected (`impact: "high"`) | `could not convert string to float: 'high'` | does not name the option or the attribute | wrap with the option id and attribute name |
| 4 | boolean used as a number (`impact: true`) | accepted as 1 | silent coercion in a utility term | reject bool where a number is expected, or document it |
| 5 | `NaN` attribute | accepted; comparisons are false so it fails closed on red lines, utilities untested | JSON cannot carry NaN, so only Python callers reach it | reject non-finite numbers |
| 6 | empty owner name, integer option id | accepted | cosmetic; receipt readability | optional validation |

Not tested yet: signed verdicts with a wrong key, replayed transcripts across two runs, `parley_check_party` with mismatched specs, concurrent calls.

## Handling

Findings 1 to 3 are worth a small PR with red-first tests after Exp 1 (current rule: do not build ahead of the current Exp); they are filed as BACKLOG rows, not code. The probe itself is a repo-private doc.

## Scope question: can Parley limit mass hacking? (2026-10-24, Oleh)

Short answer: no. Parley does not scan, patch, authenticate or monitor anything; it referees a decision among parties whose owners disagree. What it can do in this area is narrow: a verifiable record and enforced red lines for a multi-party decision such as a coordinated-disclosure timeline (`examples/demo/recipe_vuln_disclosure.json`: researcher, vendor and downstream maintainers settle on the 90-day window; "publish everything today" and "stay silent 180 days" are blocked by red lines). Limits that matter here: Parley trusts the attributes each party supplies and cannot check them against reality; a compromised agent can lie in its own spec; signatures bind a key to a verdict but there is no owner-to-key roster yet (`docs/press/PRESS-KIT.md` section 9). Context facts, secondary sources: Claude Mythos Preview exists and is restricted to Project Glasswing partners; no source was found for a claim that 70% of the internet was hacked (searched 2026-10-24).

## Receipt tamper probe, 2026-10-25 (`docs/dogfood-08/probe_receipts.py`)

What a dishonest record-keeper can get past `parley_verify_receipt` (unsigned transcripts). Each row is one rewrite of an honest run.

| Rewrite | `match` | `max_min` | Reading |
|---|---|---|---|
| nothing | true | true | baseline |
| a score edited, old hash | false | false | caught by the hash |
| a score edited, hash recomputed by the editor | true | false | the hash is trivially recomputed; the max-min replay catches the inconsistency |
| winner vetoed on the record, hash recomputed | true | false | caught by max-min |
| winner swapped to a feasible non-max-min option | false with the old hash; true with a new hash | false | caught by max-min |
| one party removed from every verdict, hash recomputed | true | **true** | **passes both checks** unless the caller pins `expected_owners` (then `max_min` false) |
| red-lined option forged acceptable for everyone and crowned, hash recomputed | true | **true** | **passes both checks**; the owner's own replay (`parley_check_party`, their private sheet) returns `holds: false` |

Conclusion. The design claim holds where it says it holds: an owner who replays their own sheet catches the forged winner (`holds: false` on the forged option, `true` on the honest one). But `parley_verify_receipt` alone proves less than its name suggests: with no pinned `expected_owners` a record with a silently dropped party verifies, and a forged all-acceptable verdict set verifies. This matches what the tool description and `PRESS-KIT.md` section 9 already say about unsigned records, but a reader who stops at `match: true, max_min_verified: true` gets false comfort.

Suggested fix (BACKLOG, after Exp 1): have the tool return the owners it found and a flag `owners_pinned: false` when `expected_owners` is absent, and name the owner replay in the same result text. Public wording rule: never describe `match` plus `max_min` as proof of non-betrayal; say tamper-evident, and that each owner's local replay is the proof.

## Signing probe, 2026-10-25 (`docs/dogfood-08/probe_signing.py`, needs pynacl)

| Case | `verify_transcript(require_signed=True)` |
|---|---|
| every verdict signed by its own owner | true |
| one signed verdict edited | false |
| a signed verdict moved to another option | false |
| all signatures stripped, default mode | **true** (fail-open downgrade; documented) |
| all signatures stripped, `require_signed=True` | false |
| coordinator signs every owner's verdict with its own single key | **true** (no owner-to-key roster; documented) |
| a genuine signed verdict replayed into another parley with the same option | **true** (no nonce; documented) |

Everything matches `SECURITY.md` and `PRESS-KIT.md` section 9: signatures give tamper evidence, not authenticity. One cheap hardening the probe suggests, not in the docs: in the "coordinator signs everything with one key" case the two supposed owners carry the same public key (1 distinct key for 2 owners). `verify_transcript` could fail when two different owners share a pubkey, or when one owner appears with two pubkeys. That does not stop a coordinator who generates one key per owner, but it removes the lazy forgery for free and needs no roster. Filed as a BACKLOG row; the owner-to-key roster pin remains the real fix.

## Concurrency probe, 2026-10-25 (`docs/dogfood-08/probe_concurrency.py`)

40 distinct specs through `tool_decide` sequentially and again on 16 threads: 0 mismatches in decision or transcript hash. No shared state found at this scale (the stdio server is single-process and serial anyway; this only checks the library path). Not covered: the HTTP demo server under load.

## Owner replay probe, 2026-10-25 (`docs/dogfood-08/probe_check_party.py`)

| Case | `holds` | Reading |
|---|---|---|
| honest winner | true | correct |
| red-lined option (`reviewed: false`) | false | correct |
| deadlock (decision null) | true | correct: no decision, nothing crossed |
| red-line attribute missing from the decision | false | fails closed, as documented |
| red-line attribute is the string `"true"` | false | strict: a string does not satisfy `== true` |
| red-line attribute is the integer `1` | **true** | `1 == True` in Python: a red line `== true` is satisfied by the number 1 |
| sheet of a party that was never in the run | true | the tool only checks the sheet you give it; it cannot know who took part |
| a sheet with no red lines | true | trivially holds |

Finding (low): equality red lines compare with Python `==`, so JSON `true` and `1` are interchangeable (and `0` equals `false`). An option that the author meant to carry `reviewed: true` could pass with `1`, and a red line written `== 1` accepts `true`. Fix: compare type and value for `==` and `!=` (bool is not int), after Exp 1. The last two rows are by design but worth one sentence in the tool description: `holds: true` speaks only about the sheet passed in, and an owner must pass their own real sheet.
