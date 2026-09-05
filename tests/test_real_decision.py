"""The Exp 1 flow, driven end to end without a human at the keyboard.

The interesting properties are not "it prints something". They are: a participant cannot
accept an outcome their own sheet rejects, a deadlock is reported honestly instead of forced,
the receipt distinguishes unanimous acceptance from an honestly computed outcome, and one
participant's position never reaches another participant's screen.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples"))

import real_decision as rd  # noqa: E402

from parley.spec import Constraint, DecisionSpec, PartySpec, UtilityTerm  # noqa: E402

OPTIONS = [
    {"id": "tue", "day": "Tuesday", "cost": 30, "reviewed": True},
    {"id": "wed", "day": "Wednesday", "cost": 90, "reviewed": True},
    {"id": "skip", "day": "Tuesday", "cost": 5, "reviewed": False},
]


def scripted(lines):
    """An `ask` that reads from a script and fails loudly when the flow asks for more."""
    it = iter(lines)

    def ask(_prompt=""):
        try:
            return next(it)
        except StopIteration:  # pragma: no cover - only on a broken test script
            raise AssertionError("the flow asked for more input than the script provides")

    return ask


def collector():
    out = []

    def say(text=""):
        out.append(str(text))

    return out, say


def party(owner, hard=(), utility=()):
    return PartySpec(owner=owner, hard=list(hard), utility=list(utility))


# --- loading the shared option set ------------------------------------------------------

def test_load_options_accepts_a_recipe_and_a_bare_list(tmp_path):
    recipe = tmp_path / "recipe.json"
    recipe.write_text(json.dumps({"title": "Pick a slot", "options": OPTIONS}))
    title, options = rd.load_options(str(recipe))
    assert title == "Pick a slot"
    assert options == OPTIONS

    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps(OPTIONS))
    title, options = rd.load_options(str(bare))
    assert options == OPTIONS


@pytest.mark.parametrize("payload", ['{"title": "x"}', '{"options": []}', '{"options": [1, 2]}'])
def test_load_options_rejects_an_unusable_file(tmp_path, payload):
    path = tmp_path / "bad.json"
    path.write_text(payload)
    with pytest.raises(ValueError):
        rd.load_options(str(path))


# --- manual position entry --------------------------------------------------------------

def test_manual_position_records_what_was_typed_and_nothing_else():
    ask = scripted(["cost <= 50", "", "day Tuesday 2", ""])
    _, say = collector()
    spec = rd.manual_position(ask, say, "Ana", OPTIONS)

    assert [(c.attr, c.op, c.value) for c in spec.hard] == [("cost", "<=", 50)]
    assert [(t.attr, t.prefer, t.weight) for t in spec.utility] == [("day", "Tuesday", 2.0)]


def test_manual_position_rejects_an_unknown_operator_before_the_parley_starts():
    ask = scripted(["cost =< 50", "cost <= 50", "", ""])
    out, say = collector()
    spec = rd.manual_position(ask, say, "Ana", OPTIONS)

    assert len(spec.hard) == 1  # the typo was refused, the correction kept
    assert any("unknown operator" in line for line in out)


def test_manual_position_keeps_a_malformed_line_out_of_the_sheet():
    ask = scripted(["cost", "", ""])
    out, say = collector()
    spec = rd.manual_position(ask, say, "Ana", OPTIONS)

    assert spec.hard == []
    assert any("three parts" in line for line in out)


# --- ratification -----------------------------------------------------------------------

def _agreed_run():
    parties = [
        party("Ana", hard=[Constraint("reviewed", "==", True)],
              utility=[UtilityTerm("cost", weight=1.0, direction="lower", lo=0, hi=90)]),
        party("Bob", utility=[UtilityTerm("day", weight=1.0, prefer="Tuesday")]),
    ]
    result = DecisionSpec("Pick a slot", OPTIONS, parties).run()
    return parties, result


def test_a_red_line_blocks_the_tempting_option():
    _, result = _agreed_run()
    assert result.status == "agreed"
    assert result.decision["id"] == "tue"  # "skip" is cheaper but unreviewed


def test_accepting_produces_a_unanimous_receipt():
    parties, result = _agreed_run()
    ask = scripted(["yes", "", "yes", ""])
    _, say = collector()

    acceptances = rd.collect_ratifications(ask, say, parties, result)
    data = rd.receipt("Pick a slot", result, acceptances, {"Ana", "Bob"})

    assert data["unanimous_acceptance"] is True
    assert data["max_min_verified"] is True
    assert [a["accepted"] for a in data["acceptances"]] == [True, True]


def test_one_declining_participant_breaks_unanimity_without_breaking_the_record():
    parties, result = _agreed_run()
    ask = scripted(["yes", "", "no", ""])
    _, say = collector()

    acceptances = rd.collect_ratifications(ask, say, parties, result)
    data = rd.receipt("Pick a slot", result, acceptances, {"Ana", "Bob"})

    assert data["unanimous_acceptance"] is False
    assert data["max_min_verified"] is True  # the coordinator still computed honestly


def test_a_participant_cannot_accept_what_their_own_sheet_rejects():
    """The screen tells them a red line was crossed, and an accept is downgraded to a decline."""
    parties, result = _agreed_run()
    # Ana signs up to a sheet that rejects the decision the parley actually reached.
    parties[0] = party("Ana", hard=[Constraint("day", "==", "Wednesday")])
    ask = scripted(["yes", "", "yes", ""])
    out, say = collector()

    acceptances = rd.collect_ratifications(ask, say, parties, result)

    assert acceptances[0].owner == "Ana"
    assert acceptances[0].accepted is False
    assert any("CROSSES a red line" in line for line in out)


def test_ratification_binds_the_exact_record():
    parties, result = _agreed_run()
    ask = scripted(["yes", "", "yes", ""])
    _, say = collector()

    acceptances = rd.collect_ratifications(ask, say, parties, result)
    assert {a.transcript_hash for a in acceptances} == {result.transcript.hash()}
    assert all(a.decision == result.decision for a in acceptances)


# --- deadlock ---------------------------------------------------------------------------

def test_deadlock_is_reported_honestly_and_forces_nothing():
    parties = [
        party("Ana", hard=[Constraint("day", "==", "Tuesday")]),
        party("Bob", hard=[Constraint("day", "==", "Wednesday")]),
    ]
    result = DecisionSpec("Impossible", OPTIONS, parties).run()
    assert result.status == "deadlock"

    data = rd.receipt("Impossible", result, [], {"Ana", "Bob"})
    out, say = collector()
    rd.report(say, data)

    assert data["decision"] is None
    assert data["unanimous_acceptance"] is False
    assert data["max_min_verified"] is True  # an honest deadlock verifies as honest
    assert any("DEADLOCK" in line for line in out)


# --- privacy ----------------------------------------------------------------------------

def test_one_participants_red_line_never_reaches_another_participants_screen():
    parties, result = _agreed_run()
    parties[0] = party("Ana", hard=[Constraint("salary_floor", ">=", 99000)])
    ask = scripted(["no", "", "yes", ""])
    out, say = collector()

    rd.collect_ratifications(ask, say, parties, result)
    printed = "\n".join(out)
    bob_screen = printed.split("Bob, review the outcome privately")[-1]

    assert "salary_floor" not in bob_screen
    assert "99000" not in bob_screen


def test_the_receipt_carries_masked_verdicts_only():
    parties, result = _agreed_run()
    ask = scripted(["yes", "", "yes", ""])
    _, say = collector()
    acceptances = rd.collect_ratifications(ask, say, parties, result)

    blob = json.dumps(rd.receipt("Pick a slot", result, acceptances, {"Ana", "Bob"}))

    assert "reviewed == True" not in blob  # no constraint description leaks
    for entry in json.loads(blob)["transcript"]["entries"]:
        for verdict in entry["verdicts"]:
            assert set(verdict) <= {"owner", "acceptable", "score", "reason", "sig", "pubkey_hex"}
            assert verdict["reason"] in ("ok", "red-line")


# --- argument handling ------------------------------------------------------------------

def test_main_refuses_a_one_sided_parley(tmp_path, monkeypatch):
    path = tmp_path / "o.json"
    path.write_text(json.dumps(OPTIONS))
    monkeypatch.setattr(rd, "_default_io", lambda: (scripted([]), lambda *_: None))

    assert rd.main(["--options", str(path), "--participants", "Ana"]) == 2


def test_main_refuses_duplicate_names(tmp_path, monkeypatch):
    path = tmp_path / "o.json"
    path.write_text(json.dumps(OPTIONS))
    monkeypatch.setattr(rd, "_default_io", lambda: (scripted([]), lambda *_: None))

    assert rd.main(["--options", str(path), "--participants", "Ana,Ana"]) == 2


def test_main_runs_the_whole_flow_in_manual_mode_and_writes_a_receipt(tmp_path, monkeypatch):
    path = tmp_path / "o.json"
    path.write_text(json.dumps({"title": "Pick a slot", "options": OPTIONS}))
    out_path = tmp_path / "receipt.json"

    script = [
        "",                                          # options agreed
        "reviewed == true", "", "cost 30 1", "", "",  # Ana: red line, end; preference, end; hand over
        "", "day Tuesday 1", "", "",                  # Bob: no red line; preference, end; hand over
        "yes", "", "yes", "",                         # both ratify
    ]
    monkeypatch.setattr(rd, "_default_io", lambda: (scripted(script), lambda *_: None))

    code = rd.main(["--options", str(path), "--participants", "Ana,Bob",
                    "--manual", "--receipt", str(out_path)])

    assert code == 0
    data = json.loads(out_path.read_text())
    assert data["status"] == "agreed"
    assert data["decision"]["id"] == "tue"
    assert data["unanimous_acceptance"] is True
    assert data["max_min_verified"] is True
    assert len(data["transcript_hash"]) == 64
