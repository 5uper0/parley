"""O7 simulation: does a party who shades its soft scores gain under Parley's max-min rule?

Runs the real `parley.consensus.run_consensus` over `parley.agent.Agent` delegates. Party 0 is
the liar; every other party reports its true utility. Red lines are identical in the honest and
the lying run (except strategy `fake_redlines`, which is the separate veto attack), so only the
soft score moves the outcome. Liar gain = liar's TRUE utility of the lying-run decision minus
its TRUE utility of the honest-run decision.

Mitigation column: `ordinal` replaces every party's reported score with its strict rank among
the options (normalised to [0, 1]), computed by the delegate before the verdict leaves. A liar
can then only misreport an order, not a magnitude.

Run from the repo root: .venv/bin/python docs/dogfood-08/sim_o7_score_shading.py
"""
import random
import statistics

from parley.agent import Agent
from parley.consensus import run_consensus
from parley.preferences import HardConstraint, PreferenceSheet

SEED = 20261025
DRAWS = 5000
THRESHOLD = 0.30


def make_agent(owner, banned, scores):
    hard = [HardConstraint("rl", lambda o, b=frozenset(banned): o not in b)]
    return Agent(owner, PreferenceSheet(owner, hard=hard, utility=lambda o, s=dict(scores): s[o]))


def to_ordinal(scores, tiebreak):
    """Strict rank, 1.0 for the top option, 0.0 for the bottom; ties broken by `tiebreak`."""
    order = sorted(scores, key=lambda o: (scores[o], tiebreak[o]))
    m = len(order)
    return {o: i / (m - 1) for i, o in enumerate(order)}


def decide(parties, ordinal):
    agents = []
    for owner, banned, reported, true in parties:
        rep = to_ordinal(reported, true) if ordinal else reported
        agents.append(make_agent(owner, banned, rep))
    options = list(parties[0][3])
    return run_consensus(agents, options).decision


def lie(strategy, true, banned, feasible_all, honest_winner, outcome):
    """Return (reported scores, reported banned set) for the liar."""
    mine_ok = [o for o in true if o not in banned]
    fav = max(mine_ok, key=lambda o: true[o]) if mine_ok else None
    if strategy == "inflate_fav_zero_rest":
        return {o: (1.0 if o == fav else 0.0) for o in true}, banned
    if strategy == "top1_high":
        return {o: (1.0 if o == fav else true[o]) for o in true}, banned
    if strategy == "stretch":
        lo, hi = min(true.values()), max(true.values())
        return {o: (true[o] - lo) / (hi - lo) if hi > lo else 0.5 for o in true}, banned
    if strategy == "bury_honest_winner":
        # informed: knows the honest outcome (e.g. from a previous public transcript)
        rep = dict(true)
        if honest_winner is not None and honest_winner != fav:
            rep[honest_winner] = 0.0
        return rep, banned
    if strategy == "informed_best_response":
        # knows every other party's reported scores and the all-feasible set (both are on the
        # public transcript of an earlier run). Tries targets from its best down: target on top,
        # every other all-feasible option at the bottom, and keeps the first report that wins.
        for target in sorted(feasible_all, key=lambda o: -true[o]):
            rep = {o: (1.0 if o == target else 0.0 if o in feasible_all else 0.5) for o in true}
            if outcome(rep) == target:
                return rep, banned
        return dict(true), banned
    if strategy == "fake_redlines":
        # not a score attack: declares every option but its favourite a red line
        return dict(true), set(true) - ({fav} if fav is not None else set())
    raise ValueError(strategy)


STRATEGIES = ["inflate_fav_zero_rest", "top1_high", "stretch", "bury_honest_winner",
              "informed_best_response", "fake_redlines"]


def simulate(n_parties, strategy, p_redline, ordinal, seed):
    rng = random.Random(seed)
    gains, honest_delta, floor_delta = [], [], []
    win = lose = same = deadlock_honest = new_deadlock = could_gain = 0
    for _ in range(DRAWS):
        m = rng.randint(4, 8)
        opts = list(range(m))
        true = [{o: rng.random() for o in opts} for _ in range(n_parties)]
        banned = [{o for o in opts if rng.random() < p_redline} for _ in range(n_parties)]
        honest = [(f"P{i}", banned[i], true[i], true[i]) for i in range(n_parties)]
        d_h = decide(honest, ordinal)
        if d_h is None:
            deadlock_honest += 1
            continue
        feasible_all = [o for o in opts if all(o not in b for b in banned)]
        if true[0][d_h] < max(true[0][o] for o in feasible_all):
            could_gain += 1
        outcome = lambda r: decide([("P0", banned[0], r, true[0])] + honest[1:], ordinal)
        rep, rep_banned = lie(strategy, true[0], banned[0], feasible_all, d_h, outcome)
        lying = [("P0", rep_banned, rep, true[0])] + honest[1:]
        d_l = decide(lying, ordinal)
        if d_l is None:
            new_deadlock += 1
            continue
        g = true[0][d_l] - true[0][d_h]
        gains.append(g)
        win += g > 1e-12
        lose += g < -1e-12
        same += abs(g) <= 1e-12
        h_true = lambda d: [true[i][d] for i in range(1, n_parties)]
        honest_delta.append(statistics.mean(h_true(d_l)) - statistics.mean(h_true(d_h)))
        floor_delta.append(min(h_true(d_l)) - min(h_true(d_h)))
    base = DRAWS - deadlock_honest
    return {
        "agreed": base, "win": win / base, "lose": lose / base, "same": same / base,
        "new_deadlock": new_deadlock / base, "could_gain": could_gain / base,
        "win_given_could": win / could_gain if could_gain else 0.0,
        "mean_gain": statistics.mean(gains) if gains else 0.0,
        "mean_gain_when_win": statistics.mean([g for g in gains if g > 1e-12]) if win else 0.0,
        "honest_mean_delta": statistics.mean(honest_delta) if honest_delta else 0.0,
        "honest_floor_delta": statistics.mean(floor_delta) if floor_delta else 0.0,
    }


def table(title, rows):
    print(f"\n## {title}\n")
    print("| N | strategy | agreed draws | liar gains | liar loses | same | new deadlock | "
          "gains / could-gain | mean gain | mean gain when it gains | honest mean Δ | honest floor Δ | >30%? |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for n, s, r in rows:
        print(f"| {n} | {s} | {r['agreed']} | {r['win']:.1%} | {r['lose']:.1%} | {r['same']:.1%} | "
              f"{r['new_deadlock']:.1%} | {r['win_given_could']:.1%} | {r['mean_gain']:+.3f} | "
              f"{r['mean_gain_when_win']:+.3f} | {r['honest_mean_delta']:+.3f} | "
              f"{r['honest_floor_delta']:+.3f} | {'YES' if r['win'] > THRESHOLD else 'no'} |")


def main():
    print(f"seed={SEED} draws={DRAWS} per row, options 4-8, utilities U[0,1], liar = party 0")
    for ordinal in (False, True):
        rows = []
        for n in (3, 4, 5):
            for s in STRATEGIES:
                rows.append((n, s, simulate(n, s, 0.2, ordinal, SEED + 100 * n)))
        table(f"{'ordinal (strict rank) scores' if ordinal else 'cardinal scores (current core)'}, "
              f"red-line probability 0.2 per party per option", rows)
    rows = []
    for p in (0.0, 0.4):
        for s in STRATEGIES[:5]:
            rows.append((3, f"{s} (p={p})", simulate(3, s, p, False, SEED + 7)))
    table("sensitivity: N=3, cardinal, red-line probability 0.0 and 0.4", rows)


if __name__ == "__main__":
    main()
