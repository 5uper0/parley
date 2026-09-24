"""Consensus among delegates with CONFLICTING private interests.

The coordinator sees only Verdicts (never the sheets). A decision is valid only
if it is feasible for EVERY agent (all red lines pass). Among feasible options it
picks by an egalitarian rule (maximise the least-happy agent) — social choice,
not majority vote. If no option is feasible for all, it is an honest deadlock,
never a forced bad decision.
"""
import pytest

from parley.preferences import PreferenceSheet, HardConstraint
from parley.agent import Agent
from parley.consensus import run_consensus, verify_outcome


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


def test_verify_outcome_accepts_honest_transcript():
    from parley.consensus import verify_outcome
    r = run_consensus([ana(), bob()], OPTIONS)
    assert verify_outcome(r.transcript) is True


def test_verify_outcome_rejects_non_maxmin_decision():
    # A dishonest coordinator swaps the finalized decision to a feasible-but-not-max-min option.
    from parley.consensus import verify_outcome
    r = run_consensus([ana(), bob()], OPTIONS)
    assert r.decision == slot("tue", 12)          # the honest max-min winner
    r.transcript.finalize(status="agreed", decision=slot("mon", 15))  # tampered
    assert verify_outcome(r.transcript) is False


def test_verify_outcome_rejects_infeasible_decision():
    from parley.consensus import verify_outcome
    r = run_consensus([ana(), bob()], OPTIONS)
    r.transcript.finalize(status="agreed", decision=slot("fri", 16))  # bob red-lines friday
    assert verify_outcome(r.transcript) is False


def test_verify_outcome_accepts_honest_deadlock():
    from parley.consensus import verify_outcome
    picky = Agent("picky", PreferenceSheet(
        owner="picky", hard=[HardConstraint("impossible", lambda o: False)]))
    r = run_consensus([ana(), picky], OPTIONS)
    assert r.status == "deadlock"
    assert verify_outcome(r.transcript) is True


# ---------- edge shapes: the red-line AND and the honest deadlock must hold at every size ----------

def test_no_options_is_an_honest_deadlock():
    r = run_consensus([ana(), bob()], [])
    assert (r.status, r.decision) == ("deadlock", None)
    assert verify_outcome(r.transcript) is True


def test_no_agents_is_an_honest_deadlock_not_a_crash():
    # nobody took part, so nothing was agreed; verify_outcome already reads it that way
    r = run_consensus([], OPTIONS)
    assert (r.status, r.decision) == ("deadlock", None)
    assert verify_outcome(r.transcript) is True


def test_a_single_agent_never_gets_an_option_it_red_lined():
    solo = Agent("solo", PreferenceSheet(
        owner="solo",
        hard=[HardConstraint("no-friday", lambda o: o["day"] != "fri")],
        utility=lambda o: 1.0 if o["day"] == "fri" else 0.1,
    ))
    r = run_consensus([solo], OPTIONS)
    assert r.status == "agreed" and r.decision["day"] != "fri"


def test_an_infeasible_option_with_the_best_scores_never_wins():
    def fan(owner, hard=()):
        return Agent(owner, PreferenceSheet(owner=owner, hard=list(hard),
                                            utility=lambda o: 1.0 if o == slot("mon", 9) else 0.0))
    ana_hates_mornings = fan("ana", [HardConstraint("no-mornings", lambda o: o["hour"] >= 12)])
    r = run_consensus([ana_hates_mornings, fan("m1"), fan("m2")], OPTIONS)
    assert r.status == "agreed" and r.decision != slot("mon", 9)


def _fixed(owner, scores):
    return Agent(owner, PreferenceSheet(owner=owner, utility=lambda o: scores[o["day"]]))


def test_equal_floor_is_tie_broken_by_total_welfare():
    # both options have floor 0.4; tue carries more total welfare (1.3 vs 0.9)
    opts = [slot("mon", 15), slot("tue", 15)]
    a = _fixed("a", {"mon": 0.5, "tue": 0.9})
    b = _fixed("b", {"mon": 0.4, "tue": 0.4})
    assert run_consensus([a, b], opts).decision == slot("tue", 15)
    assert run_consensus([a, b], list(reversed(opts))).decision == slot("tue", 15)


def test_floor_outranks_total_welfare():
    # mon has the larger total (1.1 vs 1.0) but the lower floor (0.1 vs 0.5)
    opts = [slot("mon", 15), slot("tue", 15)]
    a = _fixed("a", {"mon": 1.0, "tue": 0.5})
    b = _fixed("b", {"mon": 0.1, "tue": 0.5})
    assert run_consensus([a, b], opts).decision == slot("tue", 15)


def test_an_exact_tie_goes_to_the_first_listed_option_and_verify_outcome_agrees():
    opts = [slot("mon", 15), slot("tue", 15)]
    a = _fixed("a", {"mon": 0.5, "tue": 0.5})
    b = _fixed("b", {"mon": 0.5, "tue": 0.5})
    r = run_consensus([a, b], opts)
    assert r.decision == slot("mon", 15)
    assert verify_outcome(r.transcript) is True
    r.transcript.finalize(status="agreed", decision=slot("tue", 15))  # the other half of the tie
    assert verify_outcome(r.transcript) is False


def test_duplicate_owner_names_are_refused():
    # verify_outcome requires one verdict per owner per entry, so a record with two "ana"s
    # could never verify; refuse it before anyone is asked
    other_ana = Agent("ana", PreferenceSheet(owner="ana", utility=lambda o: 0.1))
    with pytest.raises(ValueError):
        run_consensus([ana(), other_ana], OPTIONS)
    with pytest.raises(ValueError):
        run_consensus([ana(), bob(), ana()], [])


def test_unknown_rule_is_refused_even_when_nothing_is_feasible():
    with pytest.raises(ValueError):
        run_consensus([ana(), bob()], [], rule="majority")
    with pytest.raises(ValueError):
        run_consensus([ana(), bob()], OPTIONS, rule="majority")


# ---------- verify_outcome over a record the coordinator authored ----------

def _dropped_veto_record():
    # bob red-lines friday; without bob's veto fri-16 would be the max-min pick
    a = _fixed("ana", {"mon": 0.2, "fri": 0.9})
    b = Agent("bob", PreferenceSheet(owner="bob",
                                     hard=[HardConstraint("no-friday", lambda o: o["day"] != "fri")],
                                     utility=lambda o: 0.9 if o["day"] == "fri" else 0.2))
    r = run_consensus([a, b], [slot("mon", 15), slot("fri", 16)])
    assert r.decision == slot("mon", 15)
    return r.transcript


def test_verify_outcome_rejects_a_record_that_drops_an_owners_veto():
    t = _dropped_veto_record()
    fri = t.entries[1]
    fri["verdicts"] = [v for v in fri["verdicts"] if v["owner"] != "bob"]
    t.finalize(status="agreed", decision=slot("fri", 16))
    assert verify_outcome(t) is False


def test_verify_outcome_rejects_a_duplicated_verdict_standing_in_for_an_owner():
    t = _dropped_veto_record()
    fri = t.entries[1]
    ana_v = next(v for v in fri["verdicts"] if v["owner"] == "ana")
    fri["verdicts"] = [ana_v, dict(ana_v)]
    t.finalize(status="agreed", decision=slot("fri", 16))
    assert verify_outcome(t) is False


def test_verify_outcome_rejects_an_unfinalized_record():
    r = run_consensus([ana(), bob()], OPTIONS)
    r.transcript.result = None
    assert verify_outcome(r.transcript) is False


# ---------- verify_outcome against the roster the holder expects ----------

def test_dropping_an_owner_from_every_entry_passes_without_a_roster_but_not_with_one():
    t = _dropped_veto_record()
    for e in t.entries:
        e["verdicts"] = [v for v in e["verdicts"] if v["owner"] != "bob"]
    t.finalize(status="agreed", decision=slot("fri", 16))
    assert verify_outcome(t) is True  # self-consistent: bob is simply absent everywhere
    assert verify_outcome(t, expected_owners=["ana", "bob"]) is False


def test_deleting_the_lone_veto_in_a_one_option_record_is_caught_by_the_roster():
    b = Agent("bob", PreferenceSheet(owner="bob",
                                     hard=[HardConstraint("no-friday", lambda o: o["day"] != "fri")],
                                     utility=lambda o: 0.5))
    r = run_consensus([_fixed("ana", {"fri": 0.9}), b], [slot("fri", 16)])
    assert r.status == "deadlock"
    t = r.transcript
    t.entries[0]["verdicts"] = [v for v in t.entries[0]["verdicts"] if v["owner"] != "bob"]
    t.finalize(status="agreed", decision=slot("fri", 16))
    assert verify_outcome(t) is True
    assert verify_outcome(t, expected_owners={"ana", "bob"}) is False


def test_an_honest_record_passes_against_its_own_roster():
    r = run_consensus([ana(), bob()], OPTIONS)
    assert verify_outcome(r.transcript, expected_owners=("bob", "ana")) is True
    assert verify_outcome(r.transcript, expected_owners=["ana", "bob", "cara"]) is False
    assert verify_outcome(r.transcript, expected_owners=["ana", "ana", "bob"]) is False
