"""A Transcript makes the outcome VERIFIABLE and tamper-evident.

Each owner can locally replay their own private sheet against the final decision
to prove their agent never crossed a red line ("non-betrayal") — without anyone
else seeing the sheet. Any edit to the record changes its hash.
"""
from parley.preferences import PreferenceSheet, HardConstraint
from parley.agent import Agent
from parley.consensus import run_consensus


def slot(day, hour):
    return {"day": day, "hour": hour}


OPTIONS = [slot("mon", 15), slot("tue", 12), slot("fri", 9)]


def ana():
    return Agent("ana", PreferenceSheet(
        owner="ana",
        hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 12)],
        utility=lambda o: 0.7,
    ))


def bob():
    return Agent("bob", PreferenceSheet(
        owner="bob",
        hard=[HardConstraint("no-friday", lambda o: o["day"] != "fri")],
        utility=lambda o: 0.8,
    ))


def test_hash_is_deterministic():
    t1 = run_consensus([ana(), bob()], OPTIONS).transcript
    t2 = run_consensus([ana(), bob()], OPTIONS).transcript
    assert t1.hash() == t2.hash()


def test_tampering_changes_the_hash():
    t = run_consensus([ana(), bob()], OPTIONS).transcript
    before = t.hash()
    t.entries[0]["verdicts"][0]["acceptable"] = not t.entries[0]["verdicts"][0]["acceptable"]
    assert t.hash() != before


def test_owner_can_prove_non_betrayal_locally():
    r = run_consensus([ana(), bob()], OPTIONS)
    # ana replays HER private sheet against the agreed decision: red lines held?
    assert r.transcript.verify_non_betrayal(ana().sheet, r.decision) is True


def test_non_betrayal_would_fail_if_decision_violated_a_red_line():
    r = run_consensus([ana(), bob()], OPTIONS)
    friday_morning = slot("fri", 9)  # violates both ana and bob
    assert r.transcript.verify_non_betrayal(ana().sheet, friday_morning) is False
