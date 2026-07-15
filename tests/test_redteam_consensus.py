"""Red team: strategic misreport against the max-min CONSENSUS rule itself.

`test_redteam.py` pins the NET layer (auth, rate-limit, extraction). This file pins the
consensus layer: what a lying / colluding delegate can and cannot do to the outcome. The
seam that lets `RemoteAgent` stand in for a local `Agent` also lets an attacker-controlled
delegate stand in — so a liar is just any object with `.owner` + `.consider()` that reports
an attacker-chosen `Verdict` instead of evaluating an honest sheet.

The honest result max-min gives:

  * SAFETY holds — no strategic report can push an option past an *honest* agent's red
    line. Feasibility is a hard AND over all agents; a liar cannot forge another agent's
    acceptance. Non-betrayal is manipulation-proof.
  * STRATEGY-PROOFNESS does NOT hold on the soft layer — a liar can shift the pick *among
    mutually-feasible options* by inflating its score, and can force an honest DEADLOCK by
    falsely vetoing. Both harms are BOUNDED to the feasible set (never a crossed red line)
    and motivate the Byzantine/collusion research track (Exp 4).

These tests are the executable statement of that boundary. Keep them green.
"""
from parley.agent import Agent, Verdict
from parley.preferences import PreferenceSheet, HardConstraint
from parley.consensus import run_consensus


def slot(day, hour):
    return {"day": day, "hour": hour}


OPTIONS = [slot("mon", 9), slot("mon", 15), slot("tue", 12), slot("fri", 16)]


def ana():
    # honest: bans mornings (hour < 12), likes tuesdays
    return Agent("ana", PreferenceSheet(
        owner="ana",
        hard=[HardConstraint("no-mornings", lambda o: o["hour"] >= 12)],
        utility=lambda o: 1.0 if o["day"] == "tue" else 0.5,
    ))


def bob():
    # honest: bans fridays, likes 15:00
    return Agent("bob", PreferenceSheet(
        owner="bob",
        hard=[HardConstraint("no-friday", lambda o: o["day"] != "fri")],
        utility=lambda o: 1.0 if o["hour"] == 15 else 0.6,
    ))


class Liar:
    """A delegate that reports an attacker-chosen verdict, ignoring any honest sheet.

    Same `.owner`/`.consider()` interface `run_consensus` sees for every agent — the
    coordinator cannot tell it apart from an honest one, which is exactly the point.
    """

    def __init__(self, owner, verdict_for):
        self.owner = owner
        self._verdict_for = verdict_for  # option -> Verdict

    def consider(self, option):
        return self._verdict_for(option)


def _accept_all_max():
    return lambda o: Verdict("mallory", acceptable=True, score=1.0, reason="ok")


# --- SAFETY: what a liar can NEVER do ---------------------------------------

def test_liar_cannot_push_an_option_past_an_honest_red_line():
    # mallory reports acceptable+max on every option, trying to drag in a morning ana forbids.
    liar = Liar("mallory", _accept_all_max())
    r = run_consensus([ana(), liar], OPTIONS)
    assert r.status == "agreed"
    # whatever wins still clears ana's REAL red line — the lie couldn't cross it.
    assert r.decision["hour"] >= 12


def test_collusion_cannot_overrule_a_single_honest_red_line():
    # two colluders push hard for mon-9 (a morning ana red-lines); ana alone vetoes it.
    target = slot("mon", 9)

    def love_target(owner):
        return lambda o: Verdict(owner, acceptable=True, score=(1.0 if o == target else 0.0), reason="ok")

    c1 = Liar("m1", love_target("m1"))
    c2 = Liar("m2", love_target("m2"))
    r = run_consensus([ana(), c1, c2], OPTIONS)
    assert r.decision != target                      # the collusion target never wins
    if r.status == "agreed":
        assert r.decision["hour"] >= 12              # ana is not betrayed, whatever wins


# --- LIVENESS: a liar CAN degrade the outcome, but only to honest failure ----

def test_false_veto_forces_deadlock_never_a_forced_bad_decision():
    # a saboteur that red-lines everything can deny agreement (max-min gives everyone a veto)...
    saboteur = Liar("mallory", lambda o: Verdict("mallory", acceptable=False, score=0.0, reason="red-line"))
    r = run_consensus([ana(), bob(), saboteur], OPTIONS)
    assert r.status == "deadlock"                    # ...but the failure is an HONEST deadlock,
    assert r.decision is None                        # never a forced betrayal of an honest party.


def test_strategic_score_shifts_pick_only_within_the_feasible_set():
    # honest ana+bob pick tue-12 (floor 0.6). carl is truly indifferent but LIES to prefer mon-15.
    def carl_lie(o):
        return Verdict("carl", acceptable=True, score=(1.0 if o == slot("mon", 15) else 0.0), reason="ok")

    r = run_consensus([ana(), bob(), Liar("carl", carl_lie)], OPTIONS)
    # the lie moved the pick off the honest max-min optimum (tue-12 floor drops to carl's 0.0)...
    assert r.decision == slot("mon", 15)
    assert r.decision != slot("tue", 12)
    # ...but the winner still clears EVERY honest red line — harm is bounded to feasible options.
    assert r.decision["hour"] >= 12 and r.decision["day"] != "fri"
