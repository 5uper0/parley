"""A PreferenceSheet is an owner's private position: hard red lines + soft utility."""
from parley.preferences import PreferenceSheet, HardConstraint


def slot(day, hour):
    return {"day": day, "hour": hour}


def test_feasible_when_all_hard_constraints_pass():
    sheet = PreferenceSheet(
        owner="ana",
        hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 12)],
        utility=lambda o: 1.0 if o["hour"] == 15 else 0.5,
    )
    ev = sheet.evaluate(slot("mon", 15))
    assert ev.feasible is True
    assert ev.violated == []
    assert ev.score == 1.0


def test_infeasible_lists_violated_constraint_names():
    sheet = PreferenceSheet(
        owner="ana",
        hard=[
            HardConstraint("no-mornings", lambda o: o["hour"] >= 12),
            HardConstraint("no-friday", lambda o: o["day"] != "fri"),
        ],
        utility=lambda o: 0.5,
    )
    ev = sheet.evaluate(slot("fri", 9))
    assert ev.feasible is False
    assert set(ev.violated) == {"no-mornings", "no-friday"}


def test_utility_defaults_to_neutral_when_absent():
    sheet = PreferenceSheet(owner="bob", hard=[])
    ev = sheet.evaluate(slot("tue", 10))
    assert ev.feasible is True
    assert 0.0 <= ev.score <= 1.0
