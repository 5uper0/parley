"""A Transcript makes the outcome VERIFIABLE and tamper-evident.

Each owner can locally replay their own private sheet against the final decision
to prove their agent never crossed a red line ("non-betrayal") — without anyone
else seeing the sheet. Any edit to the record changes its hash.
"""
import copy
import json

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


def test_each_verdict_field_changes_the_hash_when_tampered():
    mutations = {
        "owner": "mallory",
        "acceptable": False,
        "score": 0.123,
        "reason": "rewritten",
        "sig": "fake-signature",
        "pubkey_hex": "fake-key",
    }

    for field, value in mutations.items():
        t = run_consensus([ana(), bob()], OPTIONS).transcript
        before = t.hash()
        t.entries[0]["verdicts"][0][field] = value
        assert t.hash() != before, field


def test_entry_order_is_part_of_the_transcript_hash():
    t = run_consensus([ana(), bob()], OPTIONS).transcript
    reordered = copy.deepcopy(t)
    reordered.entries = list(reversed(reordered.entries))
    assert reordered.hash() != t.hash()


def test_owner_can_prove_non_betrayal_locally():
    r = run_consensus([ana(), bob()], OPTIONS)
    # ana replays HER private sheet against the agreed decision: red lines held?
    assert r.transcript.verify_non_betrayal(ana().sheet, r.decision) is True


def test_deadlock_decision_forces_nothing_on_any_owner():
    r = run_consensus([ana(), bob()], OPTIONS)
    assert r.transcript.verify_non_betrayal(ana().sheet, None) is True
    assert r.transcript.verify_non_betrayal(bob().sheet, None) is True


def test_non_betrayal_would_fail_if_decision_violated_a_red_line():
    r = run_consensus([ana(), bob()], OPTIONS)
    friday_morning = slot("fri", 9)  # violates both ana and bob
    assert r.transcript.verify_non_betrayal(ana().sheet, friday_morning) is False


def test_non_betrayal_replays_the_supplied_sheet_not_transcript_entries():
    r = run_consensus([ana(), bob()], OPTIONS)
    r.transcript.entries.clear()

    assert r.transcript.verify_non_betrayal(ana().sheet, slot("mon", 15)) is True
    assert r.transcript.verify_non_betrayal(bob().sheet, slot("fri", 15)) is False


def test_to_dict_round_trips_through_json_without_loss():
    t = run_consensus([ana(), bob()], OPTIONS).transcript
    assert json.loads(json.dumps(t.to_dict(), sort_keys=True)) == t.to_dict()
