"""DecisionSpec — declarative recipes (constraints as data, not Python) over the same engine.

The point: a recipe is shareable JSON, never executable code, so a gallery/UI is safe. spec.py
compiles the declarative form into the existing PreferenceSheet/Agent/consensus engine unchanged.
"""
import json

from parley.spec import Constraint, UtilityTerm, PartySpec, DecisionSpec


def test_constraint_ops():
    assert Constraint("x", "<=", 5).check({"x": 5}) is True
    assert Constraint("x", "<=", 5).check({"x": 6}) is False
    assert Constraint("x", "==", "a").check({"x": "a"}) is True
    assert Constraint("x", "!=", "a").check({"x": "b"}) is True
    assert Constraint("x", "in", ["a", "b"]).check({"x": "b"}) is True
    assert Constraint("x", "not_in", ["a", "b"]).check({"x": "c"}) is True


def test_constraint_missing_attr_fails_closed():
    # a red line over an attribute the option doesn't carry is treated as NOT satisfied
    assert Constraint("sanctions_ok", "==", True).check({}) is False


def test_utility_categorical_and_numeric():
    # categorical: full weight on a match, zero otherwise
    c, w = UtilityTerm("day", prefer="tue", weight=2.0).score({"day": "tue"})
    assert (c, w) == (2.0, 2.0)
    c, w = UtilityTerm("day", prefer="tue", weight=2.0).score({"day": "mon"})
    assert (c, w) == (0.0, 2.0)
    # numeric, lower-is-better, normalized on [lo, hi]
    c, w = UtilityTerm("risk", direction="lower", lo=0, hi=10, weight=1.0).score({"risk": 0})
    assert c == 1.0
    c, _ = UtilityTerm("risk", direction="lower", lo=0, hi=10).score({"risk": 10})
    assert c == 0.0


def test_party_to_sheet_feasible_and_score():
    p = PartySpec(
        "Compliance",
        hard=[Constraint("sanctions_ok", "==", True)],
        utility=[UtilityTerm("risk", direction="lower", lo=0, hi=10)],
    )
    sheet = p.to_sheet()
    ok = sheet.evaluate({"sanctions_ok": True, "risk": 0})
    assert ok.feasible is True and ok.score == 1.0
    bad = sheet.evaluate({"sanctions_ok": False, "risk": 0})
    assert bad.feasible is False and bad.violated  # red line named, but privately


def test_run_picks_max_min_and_blocks_red_line():
    spec = _kyc_spec()
    result = spec.run()
    assert result.status == "agreed"
    assert result.decision["id"] == "approve-basic"  # egalitarian middle, not reject, not full
    # the tempting high-revenue option is infeasible for someone in the transcript
    fast = [e for e in result.transcript.entries if e["option"]["id"] == "approve-fast"][0]
    assert any(v["acceptable"] is False for v in fast["verdicts"])


def test_deadlock_when_nothing_feasible():
    spec = DecisionSpec(
        "impossible",
        options=[{"id": "o", "sanctions_ok": False}],
        parties=[PartySpec("C", hard=[Constraint("sanctions_ok", "==", True)], utility=[])],
    )
    assert spec.run().status == "deadlock"


def test_non_betrayal_holds_on_decision():
    spec = _kyc_spec()
    result = spec.run()
    for p in spec.parties:
        assert result.transcript.verify_non_betrayal(p.to_sheet(), result.decision) is True


def test_json_round_trip():
    spec = _kyc_spec()
    blob = json.dumps(spec.to_dict())
    back = DecisionSpec.from_dict(json.loads(blob))
    assert back.title == spec.title
    assert back.run().decision["id"] == "approve-basic"


def _kyc_spec():
    options = [
        {"id": "reject",        "revenue": 0,  "risk": 0, "sanctions_ok": True,  "edd_done": True},
        {"id": "approve-basic", "revenue": 3,  "risk": 3, "sanctions_ok": True,  "edd_done": True},
        {"id": "approve-full",  "revenue": 8,  "risk": 6, "sanctions_ok": True,  "edd_done": True},
        {"id": "approve-fast",  "revenue": 10, "risk": 9, "sanctions_ok": False, "edd_done": False},
    ]
    parties = [
        PartySpec("Compliance",
                  hard=[Constraint("sanctions_ok", "==", True), Constraint("edd_done", "==", True)],
                  utility=[UtilityTerm("risk", direction="lower", lo=0, hi=9)]),
        PartySpec("Risk",
                  hard=[Constraint("risk", "<=", 7)],
                  utility=[UtilityTerm("risk", direction="lower", lo=0, hi=7)]),
        PartySpec("Business",
                  hard=[],
                  utility=[UtilityTerm("revenue", direction="higher", lo=0, hi=10)]),
    ]
    return DecisionSpec("Onboard a new counterparty", options=options, parties=parties)
