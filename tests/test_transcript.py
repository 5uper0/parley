"""A Transcript makes the outcome VERIFIABLE and tamper-evident.

Each owner can locally replay their own private sheet against the final decision
to prove their agent never crossed a red line ("non-betrayal") — without anyone
else seeing the sheet. Any edit to the record changes its hash.
"""
import copy
import json

import pytest

from parley.preferences import PreferenceSheet, HardConstraint
from parley.agent import Agent, Verdict
from parley.consensus import run_consensus
from parley.transcript import Transcript


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


# ---------- reconstituting a saved record ----------
#
# A receipt is only a receipt if someone else can rebuild the record from it and get the same
# hash. `from_dict` is the inverse of `to_dict`; the canonical JSON form and the digest over it
# are pinned below so a change that silently moves every existing hash cannot land unnoticed.

PINNED_AGREED = "97337ee4df2b5c2b65c53fa3ed1379228b5000ba17a9246ac7255a77201233cb"
PINNED_DEADLOCK = "dbf4c97b190016f5916b34d9619999bd5e3b3b9141f1113a47bf13f61fb7e7df"


def _pinned_agreed():
    t = Transcript()
    t.record(slot("mon", 15), [Verdict("ana", True, 0.7, "ok"), Verdict("bob", True, 0.8, "ok")])
    t.record(slot("fri", 9), [Verdict("ana", False, 0.7, "red-line"),
                              Verdict("bob", False, 0.8, "red-line", sig="00ff", pubkey_hex="ab")])
    t.finalize(status="agreed", decision=slot("mon", 15))
    return t


def _pinned_deadlock():
    t = Transcript()
    t.record(slot("fri", 9), [Verdict("ana", False, 0.7, "red-line")])
    t.finalize(status="deadlock", decision=None)
    return t


def test_known_digests_do_not_move():
    assert _pinned_agreed().hash() == PINNED_AGREED
    assert _pinned_deadlock().hash() == PINNED_DEADLOCK


def test_from_dict_round_trips_a_live_run():
    t = run_consensus([ana(), bob()], OPTIONS).transcript
    back = Transcript.from_dict(t.to_dict())
    assert back.hash() == t.hash()
    assert back.to_dict() == t.to_dict()
    assert back.result == t.result


def test_from_dict_round_trips_through_json_text():
    t = _pinned_agreed()
    back = Transcript.from_dict(json.loads(json.dumps(t.to_dict(), sort_keys=True)))
    assert back.hash() == PINNED_AGREED


def test_from_dict_round_trips_a_deadlock_with_a_null_decision():
    t = _pinned_deadlock()
    back = Transcript.from_dict(json.loads(json.dumps(t.to_dict())))
    assert back.hash() == PINNED_DEADLOCK
    assert back.result == {"status": "deadlock", "decision": None}


def test_from_dict_round_trips_an_unfinalized_record():
    t = Transcript()
    t.record(slot("mon", 15), [Verdict("ana", True, 0.7, "ok")])
    back = Transcript.from_dict(t.to_dict())
    assert back.result is None and back.hash() == t.hash()


def test_from_dict_keeps_signed_verdicts_verifiable():
    pytest.importorskip("nacl")
    from parley.net.identity import Identity, verify_transcript

    idn = Identity.generate("ana")
    t = Transcript()
    v = Verdict("ana", True, 0.7, "ok")
    t.record(slot("mon", 15), [Verdict("ana", True, 0.7, "ok", sig=idn.sign_verdict(slot("mon", 15), v),
                                       pubkey_hex=idn.card().pubkey_hex)])
    t.finalize(status="agreed", decision=slot("mon", 15))
    back = Transcript.from_dict(json.loads(json.dumps(t.to_dict())))
    assert back.hash() == t.hash()
    assert verify_transcript(back, require_signed=True) is True
    back.entries[0]["verdicts"][0]["score"] = 0.99
    assert verify_transcript(back, require_signed=True) is False


def test_from_dict_does_not_alias_the_input():
    t = _pinned_agreed()
    data = t.to_dict()
    back = Transcript.from_dict(data)
    back.entries[0]["verdicts"][0]["score"] = 0.01
    back.result["decision"] = None
    assert Transcript.from_dict(data).hash() == PINNED_AGREED


def test_from_dict_refuses_a_record_that_is_not_a_transcript():
    good = _pinned_agreed().to_dict()
    for bad in [
        [],                                                  # not an object
        {"entries": []},                                     # no result key at all
        {"entries": {}, "result": None},                     # entries not a list
        {"entries": [{"option": 1}], "result": None},        # entry without verdicts
        {"entries": [{"option": 1, "verdicts": [{"owner": "ana"}]}], "result": None},
        {"entries": [], "result": {"status": "agreed"}},     # result without decision
        {"entries": [], "result": "agreed"},                 # result not an object
        {**good, "extra": 1},                                # keys the hash would never see
    ]:
        with pytest.raises(ValueError):
            Transcript.from_dict(bad)
    with pytest.raises(ValueError):
        tampered = json.loads(json.dumps(good))
        tampered["entries"][0]["verdicts"][0]["sheet"] = {"leak": True}
        Transcript.from_dict(tampered)
