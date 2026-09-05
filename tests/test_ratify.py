"""Ratification is the owner's explicit accept, bound to the exact record, replayed on their side.

`verify_non_betrayal` proves a red line held; `ratify` turns that into an explicit "I agree"
that cannot be given for a betrayal, cannot be moved to a different record, and is never implied
by silence. The sheet goes in; nothing about it comes out. Unsigned acceptances are
tamper-evident, not authenticated; signed ones verify against a self-attested key (roster pin
is v0.2).
"""
import dataclasses
import json

import pytest

from parley.agent import Agent, Verdict
from parley.consensus import run_consensus
from parley.preferences import HardConstraint, PreferenceSheet
from parley.ratify import Acceptance, RatifyError, acceptance_payload, agreement, ratify
from parley.transcript import Transcript


def slot(day, hour):
    return {"day": day, "hour": hour}


OPTIONS = [slot("mon", 15), slot("tue", 12), slot("fri", 9)]


def ana_sheet():
    return PreferenceSheet("ana", hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 12)],
                           utility=lambda o: 0.7)


def bob_sheet():
    return PreferenceSheet("bob", hard=[HardConstraint("no-friday", lambda o: o["day"] != "fri")],
                           utility=lambda o: 0.8)


def agreed():
    return run_consensus([Agent("ana", ana_sheet()), Agent("bob", bob_sheet())], OPTIONS)


# ---------- the owner-side accept ----------

def test_accept_binds_owner_decision_and_transcript_hash():
    r = agreed()
    acc = ratify(ana_sheet(), r.transcript, accept=True)
    assert acc == Acceptance(owner="ana", decision=r.decision,
                             transcript_hash=r.transcript.hash(), accepted=True)


def test_acceptance_carries_nothing_from_the_sheet():
    r = agreed()
    acc = ratify(ana_sheet(), r.transcript, accept=True)
    blob = json.dumps(acc.to_dict(), default=str)
    assert "no-mornings" not in blob and "0.7" not in blob
    assert set(acc.to_dict()) == {"owner", "decision", "transcript_hash", "accepted",
                                  "sig", "pubkey_hex"}


def test_cannot_accept_a_decision_that_crosses_own_red_line():
    r = agreed()
    r.transcript.finalize(status="agreed", decision=slot("fri", 9))  # a coordinator swapped it
    with pytest.raises(RatifyError):
        ratify(ana_sheet(), r.transcript, accept=True)
    # rejecting is always allowed and needs no reason
    assert ratify(ana_sheet(), r.transcript, accept=False).accepted is False


def test_reject_is_recorded_and_never_counts_as_agreement():
    r = agreed()
    accs = [ratify(ana_sheet(), r.transcript, accept=True),
            ratify(bob_sheet(), r.transcript, accept=False)]
    assert agreement(r.transcript, accs) is False


def test_nothing_to_ratify_before_finalize():
    t = Transcript()
    with pytest.raises(RatifyError):
        ratify(ana_sheet(), t, accept=True)


def test_deadlock_can_be_acknowledged_but_is_not_an_agreement():
    t = Transcript()
    t.finalize(status="deadlock", decision=None)
    acc = ratify(ana_sheet(), t, accept=True)
    assert acc.decision is None and acc.accepted is True
    assert agreement(t, [acc]) is False


# ---------- unanimity over one exact record ----------

def test_agreement_is_unanimous_over_the_same_hash():
    r = agreed()
    accs = [ratify(ana_sheet(), r.transcript, accept=True),
            ratify(bob_sheet(), r.transcript, accept=True)]
    assert agreement(r.transcript, accs) is True


def test_silence_is_never_acceptance():
    r = agreed()
    only_ana = [ratify(ana_sheet(), r.transcript, accept=True)]
    assert agreement(r.transcript, only_ana) is False
    assert agreement(r.transcript, []) is False


def test_editing_the_record_orphans_every_prior_acceptance():
    r = agreed()
    accs = [ratify(ana_sheet(), r.transcript, accept=True),
            ratify(bob_sheet(), r.transcript, accept=True)]
    r.transcript.entries[0]["verdicts"][0]["score"] = 0.99
    assert agreement(r.transcript, accs) is False


def test_acceptance_cannot_be_replayed_against_another_decision():
    r = agreed()
    accs = [ratify(ana_sheet(), r.transcript, accept=True),
            ratify(bob_sheet(), r.transcript, accept=True)]
    r.transcript.finalize(status="agreed", decision=slot("tue", 12))  # feasible for both, but not what they ratified
    assert agreement(r.transcript, accs) is False


def test_a_stranger_cannot_stand_in_for_a_participant():
    r = agreed()
    ana = ratify(ana_sheet(), r.transcript, accept=True)
    mallory = dataclasses.replace(ratify(bob_sheet(), r.transcript, accept=True), owner="mallory")
    assert agreement(r.transcript, [ana, mallory]) is False


def test_unsigned_agreement_cannot_tell_a_fabricated_acceptance_from_a_real_one():
    r = agreed()
    forged = Acceptance(owner="bob", decision=r.decision, transcript_hash=r.transcript.hash(),
                        accepted=True)
    ana = ratify(ana_sheet(), r.transcript, accept=True)
    # every Acceptance field is public: without a verifier this tier is tamper-evidence only,
    # and anyone holding the transcript can write bob's acceptance for him
    assert agreement(r.transcript, [ana, forged]) is True


def test_verifier_rejects_a_fabricated_acceptance():
    r = agreed()
    ana = ratify(ana_sheet(), r.transcript, accept=True)
    forged = Acceptance(owner="bob", decision=r.decision, transcript_hash=r.transcript.hash(),
                        accepted=True, sig="deadbeef", pubkey_hex="cafe")
    assert agreement(r.transcript, [ana, forged], verifier=lambda a: a.owner == "ana") is False
    # the verifier is consulted for every acceptance, not just the suspicious one
    assert agreement(r.transcript, [ana, forged], verifier=lambda a: True) is True
    assert agreement(r.transcript, [ana, forged], verifier=lambda a: False) is False


def test_duplicate_acceptances_from_one_owner_do_not_stand_in_for_another():
    r = agreed()
    ana = ratify(ana_sheet(), r.transcript, accept=True)
    assert agreement(r.transcript, [ana, ana, ana]) is False
    ana_again = ratify(ana_sheet(), r.transcript, accept=True)
    assert agreement(r.transcript, [ana, ana_again]) is False


def test_agreed_record_with_no_decision_is_refused_and_never_an_agreement():
    t = Transcript()
    t.record(slot("mon", 15), [Verdict(owner="ana", acceptable=True, score=0.7, reason="ok"),
                               Verdict(owner="bob", acceptable=True, score=0.8, reason="ok")])
    t.finalize(status="agreed", decision=None)  # replay would short-circuit True on None
    with pytest.raises(RatifyError):
        ratify(ana_sheet(), t, accept=True)
    with pytest.raises(RatifyError):
        ratify(ana_sheet(), t, accept=False)
    forged = [Acceptance(o, None, t.hash(), True) for o in ("ana", "bob")]
    assert agreement(t, forged) is False


def test_ratify_records_an_owner_absent_from_the_transcript_but_agreement_does_not_count_them():
    r = agreed()
    cara = PreferenceSheet("cara", hard=[], utility=lambda o: 0.5)
    acc = ratify(cara, r.transcript, accept=True)
    assert acc.owner == "cara"
    both = [ratify(ana_sheet(), r.transcript, accept=True),
            ratify(bob_sheet(), r.transcript, accept=True)]
    assert agreement(r.transcript, both + [acc]) is False


def test_coordinator_trimmed_roster_is_caught_by_the_participants_set():
    cara = PreferenceSheet("cara", hard=[HardConstraint("no-monday", lambda o: o["day"] != "mon")],
                           utility=lambda o: 0.5)
    r3 = run_consensus([Agent("ana", ana_sheet()), Agent("bob", bob_sheet()), Agent("cara", cara)],
                       OPTIONS)
    assert r3.decision == slot("tue", 12)
    r2 = agreed()  # the same parley re-run without cara: mon 15 crosses cara's red line
    assert r2.decision == slot("mon", 15)
    accs = [ratify(ana_sheet(), r2.transcript, accept=True),
            ratify(bob_sheet(), r2.transcript, accept=True)]
    assert agreement(r2.transcript, accs) is True  # the derived set is coordinator-authored
    assert agreement(r2.transcript, accs, participants={"ana", "bob", "cara"}) is False
    assert agreement(r2.transcript, accs, participants={"ana", "bob"}) is True


# ---------- optional signing, same shape as Verdict ----------

def test_signer_hook_fills_sig_and_pubkey_without_the_core_importing_crypto():
    r = agreed()
    seen = []

    def signer(payload: bytes):
        seen.append(payload)
        return "deadbeef", "cafe"

    acc = ratify(ana_sheet(), r.transcript, accept=True, signer=signer)
    assert (acc.sig, acc.pubkey_hex) == ("deadbeef", "cafe")
    assert seen == [acceptance_payload("ana", r.decision, r.transcript.hash(), True)]


def test_signed_acceptance_verifies_and_tamper_fails():
    pytest.importorskip("nacl")
    from parley.net.identity import Identity, verify_acceptance

    r = agreed()
    idn = Identity.generate("ana")
    acc = ratify(ana_sheet(), r.transcript, accept=True, signer=idn.sign_acceptance)
    assert verify_acceptance(acc) is True
    assert verify_acceptance(dataclasses.replace(acc, accepted=False)) is False
    assert verify_acceptance(dataclasses.replace(acc, transcript_hash="0" * 64)) is False
    assert verify_acceptance(dataclasses.replace(acc, sig=None)) is False


def test_signed_acceptance_does_not_yet_bind_the_owner_name_to_a_known_key():
    pytest.importorskip("nacl")
    from parley.net.identity import Identity, verify_acceptance

    r = agreed()
    mallory = Identity.generate("mallory")
    as_ana = ratify(ana_sheet(), r.transcript, accept=True, signer=mallory.sign_acceptance)
    assert as_ana.owner == "ana" and as_ana.pubkey_hex == mallory.card().pubkey_hex
    # the pubkey is self-attested by the record under test, so a properly signed acceptance
    # under someone else's name verifies: the owner -> key roster pin is the v0.2 gap
    # disclosed in SECURITY.md, and this test pins the current behaviour until it lands
    # v0.2: flip to `is False` when the roster pin lands
    assert verify_acceptance(as_ana) is True


def test_agreement_with_verify_acceptance_does_not_yet_stop_a_single_key_signing_the_whole_set():
    pytest.importorskip("nacl")
    from parley.net.identity import Identity, verify_acceptance

    r = agreed()
    mallory = Identity.generate("mallory")
    forged = [ratify(ana_sheet(), r.transcript, accept=True, signer=mallory.sign_acceptance),
              ratify(bob_sheet(), r.transcript, accept=True, signer=mallory.sign_acceptance)]
    assert {a.pubkey_hex for a in forged} == {mallory.card().pubkey_hex}
    # every acceptance carries the key it is checked against, so one keypair signing under
    # both owners' names still passes the verifier: the owner -> key roster pin (v0.2,
    # SECURITY.md) is what turns this into owner authentication
    # v0.2: flip to `is False` when the roster pin lands
    assert agreement(r.transcript, forged, verifier=verify_acceptance) is True


def test_agreement_with_verify_acceptance_rejects_unsigned_and_tampered():
    pytest.importorskip("nacl")
    from parley.net.identity import Identity, verify_acceptance

    r = agreed()
    ana, bob = Identity.generate("ana"), Identity.generate("bob")
    accs = [ratify(ana_sheet(), r.transcript, accept=True, signer=ana.sign_acceptance),
            ratify(bob_sheet(), r.transcript, accept=True, signer=bob.sign_acceptance)]
    assert agreement(r.transcript, accs, verifier=verify_acceptance) is True
    unsigned_bob = ratify(bob_sheet(), r.transcript, accept=True)
    assert agreement(r.transcript, [accs[0], unsigned_bob], verifier=verify_acceptance) is False
    forged_bob = Acceptance("bob", r.decision, r.transcript.hash(), True,
                            sig=accs[1].sig[::-1], pubkey_hex=accs[1].pubkey_hex)
    assert agreement(r.transcript, [accs[0], forged_bob], verifier=verify_acceptance) is False


def test_verdict_and_acceptance_payloads_are_domain_separated():
    pytest.importorskip("nacl")
    from parley.net.identity import verdict_payload

    assert b'"type": "acceptance/0.1"' in acceptance_payload("ana", None, "0" * 64, True)
    assert b'"type": "verdict/0.1"' in verdict_payload(None, "ana", True, 0.0, "ok")
