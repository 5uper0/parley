"""Golden vectors: the Python engine's answers, frozen as JSON, so the JavaScript engine in `room/`
can be held to byte-identical verdicts and the same transcript hash.

    PYTHONPATH=. .venv/bin/python scripts/gen-golden-vectors.py          # rewrite the file
    PYTHONPATH=. .venv/bin/python scripts/gen-golden-vectors.py --check  # exit 1 if it is stale
"""
import glob
import json
import os
import sys

from parley.spec import DecisionSpec

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "tests", "golden", "engine_vectors.json")

EDGE = {
    "title": "edge: every operator, unicode ids, scores at 0 and 1, a deadlock-free pick",
    "options": [
        {"id": "ñandú-ü", "n": 3, "price": 0.1, "ok": True, "kind": "a", "tags": ["x", "y"]},
        {"id": "b", "n": 10, "price": 2.5, "ok": False, "kind": "b", "tags": []},
        {"id": "c", "n": 0, "price": 1e-7, "ok": True, "kind": "c", "tags": ["z"]},
        {"id": "d", "n": 7, "price": 100.25, "ok": True, "kind": "a", "tags": ["x"]},
    ],
    "parties": [
        {"owner": "Ana", "hard": [{"attr": "ok", "op": "==", "value": True},
                                   {"attr": "n", "op": "<=", "value": 8}],
         "utility": [{"attr": "kind", "weight": 2.0, "prefer": "a"},
                     {"attr": "price", "direction": "lower", "lo": 0, "hi": 100}]},
        {"owner": "Bo", "hard": [{"attr": "kind", "op": "!=", "value": "c"},
                                  {"attr": "n", "op": ">=", "value": 3}],
         "utility": [{"attr": "n", "direction": "higher", "lo": 0, "hi": 10}]},
        {"owner": "Cy", "hard": [{"attr": "kind", "op": "in", "value": ["a", "c"]},
                                  {"attr": "price", "op": "<", "value": 101},
                                  {"attr": "n", "op": ">", "value": 2},
                                  {"attr": "id", "op": "not_in", "value": ["b"]}],
         "utility": []},
    ],
}

DEADLOCK = {
    "title": "edge: honest deadlock",
    "options": [{"id": "a", "n": 1}, {"id": "b", "n": 2}],
    "parties": [
        {"owner": "P", "hard": [{"attr": "n", "op": "==", "value": 1}], "utility": []},
        {"owner": "Q", "hard": [{"attr": "n", "op": "==", "value": 2}], "utility": []},
    ],
}

NESTED = {
    "title": "edge: bool is not int inside containers (PR 161 parity)",
    "options": [{"id": "a", "x": [True], "m": {"k": True}}, {"id": "b", "x": [1], "m": {"k": 1}},
                {"id": "c", "x": [True, 2], "m": {"k": 1}}],
    "parties": [
        {"owner": "P", "hard": [{"attr": "x", "op": "==", "value": [1]}], "utility": []},
        {"owner": "Q", "hard": [{"attr": "m", "op": "in", "value": [{"k": 1}]},
                                 {"attr": "x", "op": "!=", "value": [True]}], "utility": []},
    ],
}

HEIRS = {
    "title": "three invented heirs, one flat (docs/dogfood-09)",
    "options": [
        {"id": "sell-now", "months_to_cash": 4, "price_pct_of_market": 85, "marta_stays_months": 2,
         "monthly_cost_per_heir": 0, "family_home_kept": False},
        {"id": "sell-in-a-year", "months_to_cash": 16, "price_pct_of_market": 100,
         "marta_stays_months": 12, "monthly_cost_per_heir": 220, "family_home_kept": False},
        {"id": "marta-buys-out-with-loan", "months_to_cash": 8, "price_pct_of_market": 92,
         "marta_stays_months": 999, "monthly_cost_per_heir": 0, "family_home_kept": True},
        {"id": "sell-in-seven-months", "months_to_cash": 7, "price_pct_of_market": 95,
         "marta_stays_months": 6, "monthly_cost_per_heir": 60, "family_home_kept": False},
    ],
    "parties": [
        {"owner": "Marta", "hard": [{"attr": "marta_stays_months", "op": ">=", "value": 6}],
         "utility": [{"attr": "family_home_kept", "prefer": True}]},
        {"owner": "Javier", "hard": [{"attr": "months_to_cash", "op": "<=", "value": 9}],
         "utility": [{"attr": "price_pct_of_market", "direction": "higher", "lo": 80, "hi": 100}]},
        {"owner": "Elena", "hard": [{"attr": "monthly_cost_per_heir", "op": "<=", "value": 100}],
         "utility": [{"attr": "price_pct_of_market", "direction": "higher", "lo": 80, "hi": 100}]},
    ],
}


def recipe_sources() -> list:
    sources = [(os.path.basename(p), json.load(open(p, encoding="utf-8")))
               for p in sorted(glob.glob(os.path.join(ROOT, "examples", "demo", "recipe_*.json")))]
    return sources + [("edge", EDGE), ("deadlock", DEADLOCK), ("nested", NESTED), ("heirs", HEIRS)]


def stored_sources() -> list:
    """The specs frozen inside the vectors file, so --check does not depend on which recipe files
    this checkout happens to carry (the private tree and the public mirror hold different ones)."""
    with open(OUT, encoding="utf-8") as fh:
        return [(c["name"], c["spec"]) for c in json.load(fh)["cases"]]


def build(sources=None) -> dict:
    cases = []
    sources = recipe_sources() if sources is None else sources
    for name, raw in sources:
        spec_in = {"title": raw["title"], "options": raw["options"], "parties": raw["parties"]}
        result = DecisionSpec.from_dict(spec_in).run()
        cases.append({
            "name": name,
            "spec": spec_in,
            "expected": {
                "status": result.status,
                "decision": result.decision,
                "transcript_hash": result.transcript.hash(),
                "entries": [{"option": e["option"], "verdicts": [
                    {k: v[k] for k in ("owner", "acceptable", "score", "reason")} for v in e["verdicts"]]}
                    for e in result.transcript.entries],
            },
        })
    return {"about": "Python engine answers, frozen. Regenerate with scripts/gen-golden-vectors.py.",
            "cases": cases}


def main() -> int:
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        text = json.dumps(build(stored_sources() if current else None), indent=1, ensure_ascii=False) + "\n"
        if current != text:
            print("tests/golden/engine_vectors.json is stale; rerun scripts/gen-golden-vectors.py")
            return 1
        return 0
    text = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {len(build()['cases'])} cases to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
