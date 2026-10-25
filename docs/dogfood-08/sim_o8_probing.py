"""O8 simulation: how fast do binary red-line verdicts leak a party's numeric threshold?

Target party has the red line `cost <= T`, T uniform on [0, 1000]. An adversary (the coordinator,
or any co-party who reads the shared transcript) proposes option lists of costs and reads the
target's `acceptable` bit per option off the transcript. Each run goes through the real
`parley.spec` + `parley.consensus.run_consensus` path. Strategy: K evenly spaced costs inside the
current interval per run (K-ary search; K=1 is bisection).

Success: |estimate - T| <= 10, i.e. 1% of the [0, 1000] range (estimate = interval midpoint).
Mitigations modelled without core changes: (a) cap K options per spec; (b) a budget of B runs
(stand-in for "the proposer cannot re-run a spec with changed options without everyone's consent").

Also measures the score channel: a verdict carries the soft score even for options that pass,
so a utility term normalised on the owner's own budget leaks T from one option.

Run from the repo root: .venv/bin/python docs/dogfood-08/sim_o8_probing.py
"""
import math
import random
import statistics

from parley.consensus import run_consensus
from parley.spec import Constraint, PartySpec, UtilityTerm
from parley.agent import Agent

SEED = 20261025
TRIALS = 2000
RANGE = 1000.0
TOL = 0.01 * RANGE
MAX_RUNS = 200


def target_agent(t, utility):
    spec = PartySpec("target", hard=[Constraint("cost", "<=", t)], utility=utility)
    return Agent("target", spec.to_sheet())


ADVERSARY = Agent("adversary", PartySpec("adversary").to_sheet())


def one_run(target, costs):
    """Return [(cost, acceptable, score)] for the target, read off the public transcript."""
    options = [{"id": f"o{i}", "cost": c} for i, c in enumerate(costs)]
    tr = run_consensus([target, ADVERSARY], options).transcript
    out = []
    for e in tr.entries:
        v = next(v for v in e["verdicts"] if v["owner"] == "target")
        out.append((e["option"]["cost"], v["acceptable"], v["score"]))
    return out


def probe(t, k, budget):
    """K-ary search for at most `budget` runs; return (runs used, final error, options used)."""
    target = target_agent(t, [])
    lo, hi, runs, used = 0.0, RANGE, 0, 0
    while runs < budget and (hi - lo) / 2 > TOL:
        costs = [lo + (hi - lo) * i / (k + 1) for i in range(1, k + 1)]
        for c, ok, _ in one_run(target, costs):
            if ok:
                lo = max(lo, c)
            else:
                hi = min(hi, c)
        runs += 1
        used += k
    return runs, abs((lo + hi) / 2 - t), used


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def main():
    rng = random.Random(SEED)
    ts = [rng.uniform(0, RANGE) for _ in range(TRIALS)]
    print(f"seed={SEED} trials={TRIALS} T~U[0,{RANGE:.0f}] success=|err|<={TOL:.0f}")

    print("\n## Unlimited runs: runs and options needed to reach 1% of range\n")
    print("| options per spec K | runs median | runs max | options queried median | "
          "success rate | theory runs = ceil(log_{K+1}(1000/20)) |")
    print("|---|---|---|---|---|---|")
    for k in (500, 100, 20, 8, 4, 2, 1):
        res = [probe(t, k, MAX_RUNS) for t in ts]
        runs = [r for r, _, _ in res]
        ok = sum(e <= TOL for _, e, _ in res) / TRIALS
        theory = math.ceil(math.log(RANGE / (2 * TOL)) / math.log(k + 1))
        print(f"| {k} | {statistics.median(runs):.0f} | {max(runs)} | "
              f"{statistics.median([u for _, _, u in res]):.0f} | {ok:.1%} | {theory} |")

    print("\n## Run budget B x option cap K: share of targets pinned to 1% and the error left\n")
    print("| K | B runs | success (|err|<=10) | median error | p95 error | within 10% of range (|err|<=100) |")
    print("|---|---|---|---|---|---|")
    for k in (1, 4, 8, 20, 500):
        for b in (1, 2, 3):
            res = [probe(t, k, b) for t in ts]
            errs = [e for _, e, _ in res]
            print(f"| {k} | {b} | {sum(e <= TOL for e in errs) / TRIALS:.1%} | "
                  f"{statistics.median(errs):.1f} | {pct(errs, 0.95):.1f} | "
                  f"{sum(e <= 100 for e in errs) / TRIALS:.1%} |")

    print("\n## Score channel: one accepted option, target's cost utility normalised on [lo, hi]\n")
    print("| utility term of the target | estimate rule | success (|err|<=10) | median error |")
    print("|---|---|---|---|")
    rows = [
        ("cost lower, lo=0, hi=T (own budget as the scale)", lambda t: [UtilityTerm("cost", direction="lower", lo=0, hi=t)]),
        ("cost lower, lo=0, hi=1000 (fixed scale)", lambda t: [UtilityTerm("cost", direction="lower", lo=0, hi=RANGE)]),
        ("no utility (neutral 0.5)", lambda t: []),
    ]
    for name, util in rows:
        errs = []
        for t in ts:
            c = 10.0  # one cheap option, fixed in advance; passes whenever T >= 10
            _, ok, s = one_run(target_agent(t, util(t)), [c])[0]
            est = c / (1 - s) if ok and s < 1 else RANGE / 2
            errs.append(abs(est - t))
        print(f"| {name} | T = cost / (1 - score) | {sum(e <= TOL for e in errs) / TRIALS:.1%} | "
              f"{statistics.median(errs):.1f} |")

    print("\n## Score on a red-lined option\n")
    t = 400.0
    agent = target_agent(t, [UtilityTerm("cost", direction="lower", lo=0, hi=RANGE)])
    for c, ok, s in one_run(agent, [300.0, 500.0]):
        print(f"cost={c:.0f} acceptable={ok} score={s:.2f}")


if __name__ == "__main__":
    main()
