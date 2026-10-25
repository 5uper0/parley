"""A red-lined verdict carries a constant score, so the record reveals only that a line was crossed.

Before 2026-10-25 a verdict with acceptable=False still carried the owner's real soft score. The
O7/O8 simulation showed what that leaks: when a party scales its utility to its own budget, one
scored option pins the hidden threshold, and every rejected option still shows a real preference.
Max-min only ranks options every party accepts, so the constant cannot change a decision; the
property test below checks that against a reference that keeps the real scores. Receipts issued
before the change must keep verifying, so an old-format transcript is kept as a fixture.
"""
import json
import pathlib
import random

import pytest

from parley import mcp
from parley.agent import Agent
from parley.consensus import run_consensus, verify_outcome
from parley.preferences import HardConstraint, PreferenceSheet
from parley.transcript import Transcript

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "pre-redline-mask-transcript.json"


def _budget_agent(budget):
    return Agent("bob", PreferenceSheet(
        "bob", hard=[HardConstraint("budget", lambda o: o["cost"] <= budget)],
        utility=lambda o: 1 - o["cost"] / budget))


def test_a_red_lined_verdict_reports_score_zero():
    v = _budget_agent(800).consider({"cost": 400})
    assert v.acceptable is True and v.score == 0.5
    v = Agent("ana", PreferenceSheet(
        "ana", hard=[HardConstraint("x", lambda o: False)], utility=lambda o: 0.5)).consider({})
    assert (v.acceptable, v.score, v.reason) == (False, 0.0, "red-line")


def test_the_real_score_of_a_rejected_option_is_not_recoverable():
    rejected = {"cost": 900}
    seen = {_budget_agent(b).consider(rejected) for b in (100, 300, 500, 700, 850)}
    seen |= {Agent("bob", PreferenceSheet(
        "bob", hard=[HardConstraint("budget", lambda o: o["cost"] <= 700)],
        utility=lambda o, u=u: u)).consider(rejected) for u in (0.0, 0.3, 0.77, 1.0)}
    assert len(seen) == 1
    (v,) = seen
    assert (v.acceptable, v.score, v.reason) == (False, 0.0, "red-line")


def _reference_decision(sheets, options):
    """Max-min over the real scores, ranked only among options every sheet accepts."""
    feasible = []
    for option in options:
        evs = [s.evaluate(option) for s in sheets]
        if all(e.feasible for e in evs):
            scores = [e.score for e in evs]
            feasible.append((option, min(scores), sum(scores)))
    if not feasible:
        return "deadlock", None
    return "agreed", max(feasible, key=lambda x: (x[1], x[2]))[0]


def _random_sheet(rng, owner, n_options):
    banned = {i for i in range(n_options) if rng.random() < rng.choice((0.0, 0.2, 0.4))}
    utils = [rng.choice((rng.random(), round(rng.random(), 1))) for _ in range(n_options)]
    return PreferenceSheet(owner, hard=[HardConstraint("ban", lambda o, b=banned: o["i"] not in b)],
                           utility=lambda o, u=utils: u[o["i"]])


def test_masking_never_changes_the_decision_over_random_sheets():
    rng = random.Random(20261025)
    agreed = deadlocked = 0
    for _ in range(3000):
        n_options, n_parties = rng.randint(1, 8), rng.randint(2, 5)
        options = [{"i": i} for i in range(n_options)]
        sheets = [_random_sheet(rng, f"p{k}", n_options) for k in range(n_parties)]
        result = run_consensus([Agent(s.owner, s) for s in sheets], options)
        assert (result.status, result.decision) == _reference_decision(sheets, options)
        assert verify_outcome(result.transcript, expected_owners=[s.owner for s in sheets])
        for entry in result.transcript.entries:
            for v in entry["verdicts"]:
                if not v["acceptable"]:
                    assert v["score"] == 0.0
        agreed += result.status == "agreed"
        deadlocked += result.status == "deadlock"
    assert agreed > 100 and deadlocked > 100  # both branches were exercised


def test_new_receipts_verify_end_to_end():
    spec = json.loads((pathlib.Path(__file__).resolve().parent.parent
                       / "examples" / "demo" / "recipe_committee.json").read_text())
    out = mcp.tool_decide({"spec": spec})
    rejected = [v for e in out["transcript"]["entries"] for v in e["verdicts"] if not v["acceptable"]]
    assert rejected and all(v["score"] == 0.0 for v in rejected)
    check = mcp.tool_verify_receipt({"transcript": out["transcript"], "sha256": out["transcript_sha256"]})
    assert check["match"] and check["max_min_verified"]


def test_an_old_format_receipt_with_real_rejected_scores_still_verifies():
    data = json.loads(FIXTURE.read_text())
    rejected = [v for e in data["transcript"]["entries"] for v in e["verdicts"] if not v["acceptable"]]
    assert rejected and all(v["score"] != 0.0 for v in rejected)  # really the old format
    t = Transcript.from_dict(data["transcript"])
    assert t.hash() == data["sha256"]
    assert verify_outcome(t, expected_owners=["Ana", "Bob", "Cara"])
    check = mcp.tool_verify_receipt({"transcript": data["transcript"], "sha256": data["sha256"]})
    assert check["match"] and check["max_min_verified"]
    bob = PreferenceSheet("Bob", hard=[HardConstraint("budget", lambda o: o["cost"] <= 700)],
                          utility=lambda o: 1 - o["cost"] / 1000)
    assert t.verify_non_betrayal(bob, t.result["decision"])


def test_signed_red_lined_verdicts_verify_old_and_new():
    pytest.importorskip("nacl")
    from dataclasses import replace
    from parley.agent import Verdict
    from parley.net.identity import Identity, verify_transcript
    ident = Identity.generate("bob")
    option = {"cost": 900}
    new = _budget_agent(700).consider(option)
    old = Verdict("bob", False, 0.1, "red-line")  # what a pre-2026-10-25 bot signed
    t = Transcript()
    for v in (new, old):
        t.record(option, [replace(v, sig=ident.sign_verdict(option, v), pubkey_hex=ident.card().pubkey_hex)])
    t.finalize(status="deadlock", decision=None)
    assert verify_transcript(t, require_signed=True)
    t.entries[0]["verdicts"][0]["score"] = 0.1  # un-masking a signed verdict breaks its signature
    assert not verify_transcript(t, require_signed=True)
