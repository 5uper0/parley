"""Opus review of the P0 hardening (2026-11-05): bypasses that failed open, and the strict-compare
change that loosened negative red lines. Each test fails on the previous commit."""
import importlib.util
import json
import os

import pytest

from parley.spec import Constraint, DecisionSpec
from parley.transcript import Transcript

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _vr():
    spec = importlib.util.spec_from_file_location("vr", os.path.join(ROOT, "scripts", "verify-receipt.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- spec: negative red lines must not be loosened by the strict compare -------------

def test_not_equal_rejects_a_value_that_only_looks_equal_by_type_confusion():
    assert Constraint("flag", "!=", False).check({"flag": 0}) is False  # 0 is not "not false": fail closed
    assert Constraint("flag", "!=", False).check({"flag": True}) is True
    assert Constraint("n", "!=", 3).check({"n": 4}) is True


def test_not_in_rejects_a_loosely_equal_member():
    assert Constraint("flag", "not_in", [False]).check({"flag": 0}) is False
    assert Constraint("x", "not_in", ["a", "b"]).check({"x": "c"}) is True


def test_constraint_values_are_validated_at_load():
    with pytest.raises(ValueError):
        Constraint.from_dict({"attr": "x", "op": "not_in", "value": "abc"})
    with pytest.raises(ValueError):
        Constraint.from_dict({"attr": "x", "op": "<=", "value": "2026-12-01"})
    with pytest.raises(ValueError):
        Constraint.from_dict({"attr": "x", "op": "<=", "value": True})


# --- transcript: bound keys must be real strings -------------------------------------

def test_null_session_or_nonce_is_rejected():
    entry = {"option": {"id": "a"}, "verdicts": [
        {"owner": "A", "acceptable": True, "score": 0.5, "reason": "ok", "sig": None,
         "pubkey_hex": None, "session": None, "nonce": None}]}
    with pytest.raises(ValueError):
        Transcript.from_dict({"entries": [entry], "result": None})


# --- identity: signatures stripped, hex case, expected_session ------------------------

nacl = pytest.importorskip("nacl")
from parley.agent import Verdict  # noqa: E402
from parley.net.identity import Identity, verify_transcript  # noqa: E402


def _signed(ident, owner, option, session=None, nonce=None):
    v = Verdict(owner, True, 0.5, "ok", session=session, nonce=nonce)
    return Verdict(owner, True, 0.5, "ok", sig=ident.sign_verdict(option, v),
                   pubkey_hex=ident.card().pubkey_hex, session=session, nonce=nonce)


def _record(verdicts, option=None):
    option = option or {"id": "a"}
    t = Transcript()
    t.record(option, verdicts)
    t.finalize("agreed", option)
    return t


def test_roster_cannot_be_bypassed_by_stripping_a_signature():
    ana, bob = Identity.generate("Ana"), Identity.generate("Bob")
    roster = {"Ana": ana.card().pubkey_hex, "Bob": bob.card().pubkey_hex}
    t = _record([_signed(ana, "Ana", {"id": "a"}), _signed(bob, "Bob", {"id": "a"})])
    t.entries[0]["verdicts"][1]["sig"] = None
    t.entries[0]["verdicts"][1]["pubkey_hex"] = None
    assert not verify_transcript(t, roster=roster)  # no require_signed: the roster alone must refuse


def test_roster_refuses_an_owner_it_does_not_list():
    ana = Identity.generate("Ana")
    t = _record([_signed(ana, "Ana", {"id": "a"})])
    t.entries[0]["verdicts"][0]["sig"] = None
    t.entries[0]["verdicts"][0]["pubkey_hex"] = None
    assert not verify_transcript(t, roster={"Bob": "00" * 32})


def test_expected_session_needs_signatures():
    ana = Identity.generate("Ana")
    t = _record([_signed(ana, "Ana", {"id": "a"}, session="S", nonce="N")])
    t.entries[0]["verdicts"][0]["sig"] = None
    t.entries[0]["verdicts"][0]["pubkey_hex"] = None
    assert not verify_transcript(t, expected_session="S")


def test_hex_case_cannot_split_one_key_into_two_owners():
    k = Identity.generate("X")
    pub = k.card().pubkey_hex
    a = Verdict("Ana", True, 0.5, "ok", sig=k.sign_verdict({"id": "a"}, Verdict("Ana", True, 0.5, "ok")),
                pubkey_hex=pub.lower())
    b = Verdict("Bob", True, 0.5, "ok", sig=k.sign_verdict({"id": "a"}, Verdict("Bob", True, 0.5, "ok")),
                pubkey_hex=pub.upper())
    assert not verify_transcript(_record([a, b]), require_signed=True)


def test_an_uppercase_roster_still_accepts_the_honest_key():
    ana = Identity.generate("Ana")
    t = _record([_signed(ana, "Ana", {"id": "a"})])
    assert verify_transcript(t, require_signed=True, roster={"Ana": ana.card().pubkey_hex.upper()})


# --- verify-receipt --roster -----------------------------------------------------------

def _unsigned_receipt():
    sys_path = os.path.join(ROOT, "tests")
    import sys
    sys.path.insert(0, sys_path)
    import test_verify_receipt as tvr
    return tvr._receipt()


def test_receipt_check_with_a_roster_fails_when_nothing_is_signed():
    report = _vr().verify(_unsigned_receipt(), roster={"Ana": "00" * 32, "Bob": "11" * 32})
    assert report["ok"] is False


def test_receipt_check_with_a_roster_uses_the_roster_as_the_owner_set():
    receipt = _unsigned_receipt()
    report = _vr().verify(receipt, roster={"Ana": "00" * 32})  # Bob is a participant the roster lacks
    assert report["ok"] is False
