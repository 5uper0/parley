"""An Agent faithfully represents its owner but never leaks the private sheet.

The ONLY thing that leaves an agent is a Verdict: acceptable + a soft score +
a MASKED reason. It must never expose which red line was crossed, nor the sheet.
This is the trust wedge — deterministic, code-enforced non-betrayal.
"""
from parley.preferences import PreferenceSheet, HardConstraint
from parley.agent import Agent


def slot(day, hour):
    return {"day": day, "hour": hour}


def make_agent(owner="ana"):
    return Agent(
        owner=owner,
        sheet=PreferenceSheet(
            owner=owner,
            hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 12)],
            utility=lambda o: 1.0 if o["hour"] == 15 else 0.4,
        ),
    )


def test_verdict_accepts_feasible_option():
    v = make_agent().consider(slot("mon", 15))
    assert v.owner == "ana"
    assert v.acceptable is True
    assert v.reason == "ok"
    assert v.score == 1.0


def test_verdict_rejects_on_red_line_with_masked_reason():
    v = make_agent().consider(slot("mon", 9))
    assert v.acceptable is False
    assert v.reason == "red-line"  # masked: does NOT say WHICH red line


def test_verdict_never_leaks_the_sheet_or_which_constraint():
    v = make_agent().consider(slot("mon", 9))
    blob = repr(v) + str(getattr(v, "__dict__", v))
    assert "no-mornings" not in blob  # the private constraint name never escapes
    assert "hard" not in getattr(v, "__dict__", {})
    assert not hasattr(v, "sheet")
