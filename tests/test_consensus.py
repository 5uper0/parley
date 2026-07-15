"""Consensus among delegates with CONFLICTING private interests.

The coordinator sees only Verdicts (never the sheets). A decision is valid only
if it is feasible for EVERY agent (all red lines pass). Among feasible options it
picks by an egalitarian rule (maximise the least-happy agent) — social choice,
not majority vote. If no option is feasible for all, it is an honest deadlock,
never a forced bad decision.
"""
from parley.preferences import PreferenceSheet, HardConstraint
from parley.agent import Agent
from parley.consensus import run_consensus


def slot(day, hour):
    return {"day": day, "hour": hour}


OPTIONS = [slot("mon", 9), slot("mon", 15), slot("tue", 12), slot("fri", 16)]


def ana():
    return Agent("ana", PreferenceSheet(
        owner="ana",
        hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 12)],
        utility=lambda o: 1.0 if o["day"] == "tue" else 0.5,
    ))


def bob():
    return Agent("bob", PreferenceSheet(
        owner="bob",
        hard=[HardConstraint("no-friday", lambda o: o["day"] != "fri")],
        utility=lambda o: 1.0 if o["hour"] == 15 else 0.6,
    ))


def test_reaches_consensus_feasible_for_all():
    r = run_consensus([ana(), bob()], OPTIONS)
    assert r.status == "agreed"
    # feasible for both = {mon-15, tue-12}; egalitarian pick is one of them
    assert r.decision in (slot("mon", 15), slot("tue", 12))
    # decision must satisfy EVERY agent's red lines
    assert r.decision["hour"] >= 12 and r.decision["day"] != "fri"


def test_egalitarian_rule_maximises_the_least_happy():
    # tue-12: ana=1.0, bob=0.6 -> min 0.6 ; mon-15: ana=0.5, bob=1.0 -> min 0.5
    # egalitarian prefers tue-12 (higher floor)
    r = run_consensus([ana(), bob()], OPTIONS)
    assert r.decision == slot("tue", 12)


def test_honest_deadlock_when_no_option_is_feasible_for_all():
    picky = Agent("cara", PreferenceSheet(
        owner="cara",
        hard=[HardConstraint("only-friday", lambda o: o["day"] == "fri")],
        utility=lambda o: 1.0,
    ))
    r = run_consensus([ana(), bob(), picky], OPTIONS)  # ana bans mornings, bob bans fri, cara demands fri
    assert r.status == "deadlock"
    assert r.decision is None


def test_coordinator_only_sees_verdicts_not_sheets():
    r = run_consensus([ana(), bob()], OPTIONS)
    dump = str(r.transcript.to_dict())
    assert "no-mornings" not in dump and "no-friday" not in dump
