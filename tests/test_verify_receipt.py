"""A receipt nobody else can check is not a receipt.

`scripts/verify-receipt.py` takes the file `examples/real_decision.py` writes and re-derives
everything that can be re-derived from public data: the transcript hash, the max-min outcome,
and the binding of every acceptance to that exact hash and decision (plus its signature when
one is present). What it cannot prove is stated in the output, not hidden — the pubkey in a
signed acceptance is self-attested, and verdict payloads carry no replay binding (SECURITY.md).
"""
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples"))

import real_decision as rd  # noqa: E402

from parley.consensus import verify_outcome  # noqa: E402
from parley.ratify import Acceptance, ratify  # noqa: E402
from parley.transcript import Transcript  # noqa: E402
from parley.spec import Constraint, DecisionSpec, PartySpec, UtilityTerm  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCRIPT = os.path.join(ROOT, "scripts", "verify-receipt.py")


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_receipt", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vr = _load_verifier()

OPTIONS = [
    {"id": "tue", "day": "Tuesday", "cost": 30, "reviewed": True},
    {"id": "wed", "day": "Wednesday", "cost": 90, "reviewed": True},
    {"id": "skip", "day": "Tuesday", "cost": 5, "reviewed": False},
]


def _parties():
    return [
        PartySpec("Ana", hard=[Constraint("reviewed", "==", True)],
                  utility=[UtilityTerm("cost", weight=1.0, direction="lower", lo=0, hi=90)]),
        PartySpec("Bob", utility=[UtilityTerm("day", weight=1.0, prefer="Tuesday")]),
    ]


def _run(parties=None):
    parties = parties or _parties()
    return parties, DecisionSpec("Pick a slot", OPTIONS, parties).run()


def _receipt(signers=None, accept=("yes", "yes")):
    parties, result = _run()
    accs = [ratify(p.to_sheet(), result.transcript, accept=(a == "yes"),
                   signer=(signers or {}).get(p.owner))
            for p, a in zip(parties, accept)]
    data = rd.receipt("Pick a slot", result, accs, {"Ana", "Bob"})
    return json.loads(json.dumps(data, sort_keys=True))  # exactly what lands on disk


def _signed_receipt():
    pytest.importorskip("nacl")
    from parley.net.identity import Identity
    return _receipt(signers={n: Identity.generate(n).sign_acceptance for n in ("Ana", "Bob")})


def _owner(report, name):
    return next(a for a in report["acceptances"] if a["owner"] == name)


# --- a receipt that checks -------------------------------------------------------------

def test_a_genuine_unsigned_receipt_verifies():
    report = vr.verify(_receipt())
    assert report["ok"] is True
    assert report["hash"]["ok"] and report["hash"]["recomputed"] == report["hash"]["claimed"]
    assert report["max_min"]["ok"] is True
    assert report["unanimous"]["recomputed"] is True
    assert {a["signature"] for a in report["acceptances"]} == {"unsigned"}


def test_a_declined_receipt_still_verifies_and_says_so():
    report = vr.verify(_receipt(accept=("yes", "no")))
    assert report["ok"] is True
    assert report["unanimous"]["recomputed"] is False
    assert _owner(report, "Bob")["accepted"] is False


def test_a_deadlock_receipt_verifies_with_no_acceptances():
    parties = [PartySpec("Ana", hard=[Constraint("day", "==", "Tuesday")]),
               PartySpec("Bob", hard=[Constraint("day", "==", "Wednesday")])]
    _, result = _run(parties)
    data = json.loads(json.dumps(rd.receipt("Impossible", result, [], {"Ana", "Bob"})))
    report = vr.verify(data)
    assert report["ok"] is True
    assert report["status"] == "deadlock" and report["acceptances"] == []
    assert report["max_min"]["recomputed"] is True


def test_a_signed_receipt_verifies_every_signature():
    report = vr.verify(_signed_receipt())
    assert report["ok"] is True
    assert {a["signature"] for a in report["acceptances"]} == {"verified"}
    assert report["unanimous"]["recomputed"] is True


# --- receipts that must fail -------------------------------------------------------------

def test_a_tampered_transcript_no_longer_matches_the_claimed_hash():
    data = _receipt()
    data["transcript"]["entries"][0]["verdicts"][0]["score"] = 0.99
    report = vr.verify(data)
    assert report["ok"] is False and report["hash"]["ok"] is False


def test_a_swapped_decision_orphans_the_acceptances():
    data = _receipt()
    wed = next(o for o in OPTIONS if o["id"] == "wed")
    data["transcript"]["result"]["decision"] = wed
    data["decision"] = wed
    report = vr.verify(data)
    assert report["ok"] is False
    assert report["hash"]["ok"] is False  # the record itself changed…
    assert all(a["bound"] is False for a in report["acceptances"])  # …and nobody accepted it


def test_a_rewritten_claim_is_caught_even_when_the_record_is_intact():
    data = _receipt(accept=("yes", "no"))
    data["unanimous_acceptance"] = True
    report = vr.verify(data)
    assert report["ok"] is False and report["unanimous"]["ok"] is False


def test_a_finalized_option_that_is_not_the_max_min_one_is_caught():
    parties, result = _run()
    wed = next(o for o in OPTIONS if o["id"] == "wed")  # feasible for both, but not max-min
    result.transcript.finalize(status="agreed", decision=wed)
    result = dataclasses.replace(result, decision=wed)
    accs = [ratify(p.to_sheet(), result.transcript, accept=True) for p in parties]
    data = json.loads(json.dumps(rd.receipt("Pick a slot", result, accs, {"Ana", "Bob"})))
    report = vr.verify(data)
    assert report["hash"]["ok"] is True
    assert report["max_min"]["recomputed"] is False and report["ok"] is False


def test_an_acceptance_from_outside_the_roster_fails():
    data = _receipt()
    data["acceptances"][1]["owner"] = "Mallory"
    report = vr.verify(data)
    assert report["ok"] is False
    assert _owner(report, "Mallory")["bound"] is False


def test_a_missing_acceptance_breaks_unanimity_but_not_the_record():
    data = _receipt()
    data["acceptances"] = data["acceptances"][:1]
    data["unanimous_acceptance"] = False
    report = vr.verify(data)
    assert report["hash"]["ok"] is True
    assert report["unanimous"]["recomputed"] is False


def test_a_signature_that_does_not_match_its_acceptance_fails():
    data = _signed_receipt()
    data["acceptances"][1]["accepted"] = False  # content changed after signing
    report = vr.verify(data)
    assert report["ok"] is False
    assert _owner(report, "Bob")["signature"] == "FAILED"
    assert _owner(report, "Ana")["signature"] == "verified"


def test_a_signature_moved_from_another_owner_fails():
    data = _signed_receipt()
    data["acceptances"][1]["sig"] = data["acceptances"][0]["sig"]
    data["acceptances"][1]["pubkey_hex"] = data["acceptances"][0]["pubkey_hex"]
    report = vr.verify(data)
    assert report["ok"] is False and _owner(report, "Bob")["signature"] == "FAILED"


def _reseal(data, drop, decision):
    """Rewrite the record as a dishonest coordinator would: drop one owner's verdicts from every
    entry, finalize, and re-hash so the receipt is self-consistent again."""
    t = Transcript.from_dict(data["transcript"])
    for e in t.entries:
        e["verdicts"] = [v for v in e["verdicts"] if v["owner"] != drop]
    t.finalize(status="agreed", decision=decision)
    assert verify_outcome(t) is True  # without the roster, the forged record recomputes cleanly
    data.update(transcript=json.loads(json.dumps(t.to_dict())), transcript_hash=t.hash(),
                status="agreed", decision=decision, max_min_verified=True, acceptances=[],
                unanimous_acceptance=False)
    return data


OWNER_SET_MSG = "not exactly the receipt's participants"
MAX_MIN_MSG = "not the max-min option"


def _errors(report):
    return " ".join(report["errors"])


def test_an_owner_dropped_from_every_entry_is_reported_as_an_owner_set_mismatch():
    tue = next(o for o in OPTIONS if o["id"] == "tue")
    report = vr.verify(_reseal(_receipt(), "Ana", tue))
    assert report["ok"] is False and report["max_min"]["recomputed"] is False
    assert OWNER_SET_MSG in _errors(report) and MAX_MIN_MSG not in _errors(report)


def test_a_lone_veto_deleted_from_a_one_option_record_is_reported_as_an_owner_set_mismatch():
    skip = next(o for o in OPTIONS if o["id"] == "skip")  # Ana red-lines it: unreviewed
    parties = [PartySpec("Ana", hard=[Constraint("reviewed", "==", True)]),
               PartySpec("Bob", utility=[UtilityTerm("day", weight=1.0, prefer="Tuesday")])]
    result = DecisionSpec("One option", [skip], parties).run()
    assert result.status == "deadlock"
    data = json.loads(json.dumps(rd.receipt("One option", result, [], {"Ana", "Bob"})))
    report = vr.verify(_reseal(data, "Ana", skip))
    assert report["ok"] is False and report["max_min"]["recomputed"] is False
    assert OWNER_SET_MSG in _errors(report) and MAX_MIN_MSG not in _errors(report)


def test_a_genuinely_non_max_min_record_keeps_the_max_min_message():
    data = _receipt()
    wed = next(o for o in OPTIONS if o["id"] == "wed")
    t = Transcript.from_dict(data["transcript"])
    t.finalize(status="agreed", decision=wed)
    data.update(transcript=json.loads(json.dumps(t.to_dict())), transcript_hash=t.hash(),
                decision=wed)
    assert MAX_MIN_MSG in _errors(vr.verify(data))
    assert OWNER_SET_MSG not in _errors(vr.verify(data))


def test_the_output_says_the_participant_list_is_coordinator_written():
    assert "participants list is itself coordinator-written" in vr.render(vr.verify(_receipt()))


def test_a_receipt_missing_a_required_field_is_refused():
    data = _receipt()
    del data["participants"]
    report = vr.verify(data)
    assert report["ok"] is False and "participants" in " ".join(report["errors"])


# --- without pynacl ------------------------------------------------------------------------

def _without_nacl(monkeypatch):
    monkeypatch.setitem(sys.modules, "nacl", None)
    monkeypatch.setitem(sys.modules, "parley.net.identity", None)


def test_an_unsigned_receipt_verifies_without_pynacl(monkeypatch):
    data = _receipt()
    _without_nacl(monkeypatch)
    assert vr._crypto() is None
    report = vr.verify(data)
    assert report["ok"] is True
    assert {a["signature"] for a in report["acceptances"]} == {"unsigned"}


def test_a_signed_receipt_is_not_called_verified_without_pynacl(monkeypatch):
    data = _signed_receipt()
    _without_nacl(monkeypatch)
    report = vr.verify(data)
    assert report["ok"] is False
    assert {a["signature"] for a in report["acceptances"]} == {"unchecked"}
    assert any("parley[crypto]" in e for e in report["errors"])


# --- what the output says ------------------------------------------------------------------

def test_output_states_what_was_and_was_not_proved():
    text = vr.render(vr.verify(_receipt()))
    assert "VERIFIED" in text
    assert "does NOT prove" in text
    assert "replay" in text and "self-attested" in text
    assert "sheet" in text  # the verifier never sees one, and says so


def test_cli_exit_codes_and_report(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_receipt(), indent=2))
    proc = subprocess.run([sys.executable, SCRIPT, str(good)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VERIFIED" in proc.stdout and "does NOT prove" in proc.stdout

    bad = tmp_path / "bad.json"
    data = _receipt()
    data["transcript"]["entries"][0]["verdicts"][1]["acceptable"] = False
    bad.write_text(json.dumps(data))
    proc = subprocess.run([sys.executable, SCRIPT, str(bad)], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "FAILED" in proc.stdout

    proc = subprocess.run([sys.executable, SCRIPT, str(tmp_path / "missing.json")],
                          capture_output=True, text=True)
    assert proc.returncode == 2


@pytest.mark.parametrize("participants", [None, "Ana,Bob", [], ["Ana", "Ana", "Bob"], [1, 2]])
def test_malformed_participants_fail_the_check_without_a_traceback(tmp_path, participants):
    # a readable receipt with a bad field is a failed check (exit 1), like a missing field;
    # exit 2 stays reserved for a file that cannot be read as JSON at all
    data = _receipt()
    data["participants"] = participants
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(data))
    proc = subprocess.run([sys.executable, SCRIPT, str(path)], capture_output=True, text=True)
    assert proc.returncode == 1, proc.stderr
    assert "Traceback" not in proc.stderr
    mm_line = next(ln for ln in proc.stdout.splitlines() if "max-min honest" in ln)
    assert "owner set unchecked: participants malformed" in mm_line and mm_line.endswith("FAIL")
