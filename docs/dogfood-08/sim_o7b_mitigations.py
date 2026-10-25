"""O7b simulation: do commit-reveal, ordinal scores or a score budget remove the O7 shading gain?

Extends `sim_o7_score_shading.py` (same generators, seeds, strategies, metrics, 5,000 draws per
row, N = 3, 4, 5, p = 0.2) to mitigations that are NOT built. Every honest and lying decision is
taken by the real `parley.consensus.run_consensus` over `parley.agent.Agent` delegates; the
mitigation is modelled as a transform each delegate applies to its reported scores before its
verdict leaves:

- cardinal: no transform (the current core).
- ordinal_true: strict rank in [0, 1], ties broken by the delegate's true utility (O7's variant).
- ordinal_index: strict rank in [0, 1], ties broken by option index (lower index ranks higher).
- bounded: each delegate's scores are divided by their sum over its own acceptable options, so
  every party spends a budget of 1.0 (all-zero report -> uniform budget).

Sealed commit-reveal is modelled by what the liar knows: nothing about the other parties' scores
before it commits. `informed_best_response` and `bury_honest_winner` need the realised scores or
outcome, so under sealing they are replaced by a best response against a prior:

- sealed_br_prior: others' scores ~ U[0, 1] i.i.d. and others' red lines ~ Bernoulli(p), the
  true generating distribution (favourable to the liar).
- sealed_br_acceptance: as above, but every party's red-line acceptance per option is public
  (for example from an earlier masked transcript); only scores are sampled.

The best response picks, from a fixed candidate family, the report with the highest expected
true utility over K Monte Carlo samples, evaluated through the same transform. Inside that
search the liar uses `fast_decide`, a replica of the max-min rule; it is asserted equal to
`run_consensus` on every honest draw.

Run from the repo root: .venv/bin/python docs/dogfood-08/sim_o7b_mitigations.py
"""
import random
import statistics
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sim_o7_score_shading as o7  # noqa: E402

from parley.consensus import run_consensus  # noqa: E402

SEED, DRAWS, THRESHOLD, P = o7.SEED, o7.DRAWS, o7.THRESHOLD, 0.2
K_SAMPLES = 48
OPEN = ["inflate_fav_zero_rest", "top1_high", "stretch", "bury_honest_winner",
        "informed_best_response", "fake_redlines"]
SEALED = ["inflate_fav_zero_rest", "top1_high", "stretch", "sealed_br_prior",
          "sealed_br_acceptance", "fake_redlines"]


def transform(scheme, reported, banned, true):
    if scheme == "cardinal":
        return dict(reported)
    if scheme == "ordinal_true":
        return o7.to_ordinal(reported, true)
    if scheme == "ordinal_index":
        return o7.to_ordinal(reported, {o: -o for o in reported})
    if scheme == "bounded":
        acc = [o for o in reported if o not in banned]
        clip = {o: max(0.0, min(1.0, reported[o])) for o in reported}
        tot = sum(clip[o] for o in acc)
        if tot <= 0:
            return {o: (1.0 / len(acc) if o in acc else 0.0) for o in reported}
        return {o: (clip[o] / tot if o in acc else 0.0) for o in reported}
    raise ValueError(scheme)


def decide(parties, scheme):
    agents = [o7.make_agent(owner, banned, transform(scheme, rep, banned, true))
              for owner, banned, rep, true in parties]
    return run_consensus(agents, list(parties[0][3])).decision


def fast_decide(scores, banned, opts):
    best, key = None, None
    for o in opts:
        if any(o in b for b in banned):
            continue
        col = [max(0.0, min(1.0, s[o])) for s in scores]
        k = (min(col), sum(col))
        if key is None or k > key:
            best, key = o, k
    return best


def candidates(true0, banned0, known):
    acc = sorted((o for o in true0 if o not in banned0), key=lambda o: -true0[o])
    out = [dict(true0)]
    for k in range(1, len(acc) + 1):
        top = set(acc[:k])
        out.append({o: (1.0 if o in top else 0.0) for o in true0})
    for x in acc[1:]:
        out.append({o: (0.0 if o == x else true0[o]) for o in true0})
    if known is not None:
        feasible_all = [o for o in acc if all(o not in b for b in known)]
        for t in feasible_all:
            out.append({o: (1.0 if o == t else 0.0 if o in feasible_all else 0.5) for o in true0})
    return out


def sealed_br(scheme, true0, banned0, n, known, rng):
    opts = list(true0)
    samples = []
    for _ in range(K_SAMPLES):
        sc, bn = [], []
        for j in range(n - 1):
            t = {o: rng.random() for o in opts}
            b = known[j] if known is not None else {o for o in opts if rng.random() < P}
            sc.append(transform(scheme, t, b, t))
            bn.append(b)
        samples.append((sc, bn))
    best, best_eu = None, None
    for cand in candidates(true0, banned0, known):
        t0 = transform(scheme, cand, banned0, true0)
        eu = 0.0
        for sc, bn in samples:
            d = fast_decide([t0] + sc, [banned0] + bn, opts)
            if d is not None:
                eu += true0[d]
        if best_eu is None or eu > best_eu + 1e-12:
            best, best_eu = cand, eu
    return best


def simulate(job):
    n, strategy, scheme, seed = job
    rng = random.Random(seed)
    gains, honest_delta, floor_delta = [], [], []
    win = lose = same = deadlock_honest = new_deadlock = could_gain = 0
    for idx in range(DRAWS):
        m = rng.randint(4, 8)
        opts = list(range(m))
        true = [{o: rng.random() for o in opts} for _ in range(n)]
        banned = [{o for o in opts if rng.random() < P} for _ in range(n)]
        honest = [(f"P{i}", banned[i], true[i], true[i]) for i in range(n)]
        d_h = decide(honest, scheme)
        assert d_h == fast_decide([transform(scheme, t, b, t) for t, b in zip(true, banned)],
                                  banned, opts)
        if d_h is None:
            deadlock_honest += 1
            continue
        feasible_all = [o for o in opts if all(o not in b for b in banned)]
        if true[0][d_h] < max(true[0][o] for o in feasible_all):
            could_gain += 1
        if strategy.startswith("sealed_br"):
            known = banned[1:] if strategy == "sealed_br_acceptance" else None
            rep = sealed_br(scheme, true[0], banned[0], n, known, random.Random(seed * 100003 + idx))
            rep_banned = banned[0]
        else:
            outcome = lambda r: decide([("P0", banned[0], r, true[0])] + honest[1:], scheme)
            rep, rep_banned = o7.lie(strategy, true[0], banned[0], feasible_all, d_h, outcome)
        d_l = decide([("P0", rep_banned, rep, true[0])] + honest[1:], scheme)
        if d_l is None:
            new_deadlock += 1
            continue
        g = true[0][d_l] - true[0][d_h]
        gains.append(g)
        win += g > 1e-12
        lose += g < -1e-12
        same += abs(g) <= 1e-12
        h_true = lambda d: [true[i][d] for i in range(1, n)]
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


def social_cost(n):
    """Everyone honest: true welfare of the chosen option under each scheme, same draws."""
    rng = random.Random(SEED + 100 * n)
    acc = {s: ([], [], 0) for s in ("cardinal", "ordinal_index", "bounded")}
    for _ in range(DRAWS):
        m = rng.randint(4, 8)
        opts = list(range(m))
        true = [{o: rng.random() for o in opts} for _ in range(n)]
        banned = [{o for o in opts if rng.random() < P} for _ in range(n)]
        honest = [(f"P{i}", banned[i], true[i], true[i]) for i in range(n)]
        d_c = decide(honest, "cardinal")
        if d_c is None:
            continue
        for s in acc:
            d = d_c if s == "cardinal" else decide(honest, s)
            u = [true[i][d] for i in range(n)]
            means, floors, diff = acc[s]
            means.append(statistics.mean(u))
            floors.append(min(u))
            acc[s] = (means, floors, diff + (d != d_c))
    return {s: (statistics.mean(a), statistics.mean(b), c / len(a)) for s, (a, b, c) in acc.items()}


SECTIONS = [
    ("(a) cardinal, open (control: current core)", "cardinal", OPEN),
    ("(b) cardinal + sealed commit-reveal", "cardinal", SEALED),
    ("(c) ordinal (index tie-break) + sealed commit-reveal", "ordinal_index", SEALED),
    ("(d) ordinal (true-utility tie-break), open (control: O7 ordinal)", "ordinal_true", OPEN),
    ("(d') ordinal (index tie-break), open", "ordinal_index", OPEN),
    ("(e1) bounded budget 1.0, open", "bounded", OPEN),
    ("(e2) bounded budget 1.0 + sealed commit-reveal", "bounded", SEALED),
]


def main():
    print(f"seed={SEED} draws={DRAWS} per row, options 4-8, utilities U[0,1], p={P}, "
          f"liar = party 0, K={K_SAMPLES} prior samples for sealed best responses")
    jobs = sorted({(n, s, scheme, SEED + 100 * n)
                   for _, scheme, strats in SECTIONS for n in (3, 4, 5) for s in strats})
    with Pool() as pool:
        res = dict(zip(jobs, pool.map(simulate, jobs)))
        costs = dict(zip((3, 4, 5), pool.map(social_cost, (3, 4, 5))))
    for title, scheme, strats in SECTIONS:
        print(f"\n## {title}\n")
        print("| N | strategy | agreed | liar gains | liar loses | new deadlock | could-gain | "
              "gains / could-gain | mean gain | mean gain when it gains | honest mean Δ | "
              "honest floor Δ | >30%? |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for n in (3, 4, 5):
            for s in strats:
                r = res[(n, s, scheme, SEED + 100 * n)]
                print(f"| {n} | {s} | {r['agreed']} | {r['win']:.1%} | {r['lose']:.1%} | "
                      f"{r['new_deadlock']:.1%} | {r['could_gain']:.1%} | "
                      f"{r['win_given_could']:.1%} | {r['mean_gain']:+.3f} | "
                      f"{r['mean_gain_when_win']:+.3f} | {r['honest_mean_delta']:+.3f} | "
                      f"{r['honest_floor_delta']:+.3f} | {'YES' if r['win'] > THRESHOLD else 'no'} |")
    print("\n## social cost: everyone honest, true utility of the chosen option, same draws\n")
    print("| N | scheme | mean welfare | Δ vs cardinal | mean floor | Δ vs cardinal | "
          "decision differs from cardinal |")
    print("|---|---|---|---|---|---|---|")
    for n in (3, 4, 5):
        cw, cf, _ = costs[n]["cardinal"]
        for s, (w, f, d) in costs[n].items():
            print(f"| {n} | {s} | {w:.4f} | {w - cw:+.4f} | {f:.4f} | {f - cf:+.4f} | {d:.1%} |")


if __name__ == "__main__":
    main()
