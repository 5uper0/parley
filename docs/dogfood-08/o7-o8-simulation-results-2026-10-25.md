# O7 and O8 simulation results, 2026-10-25

Objections raised in an internal adversarial research pass (score shading O7, threshold probing O8). Both scripts are stdlib plus the zero-dependency `parley` core, use fixed seeds, and call the real engine (`run_consensus`, `Agent`, `PreferenceSheet`, `parley.spec`). No core file was changed.

```
.venv/bin/python docs/dogfood-08/sim_o7_score_shading.py   # ~20 s
.venv/bin/python docs/dogfood-08/sim_o8_probing.py         # ~22 s
```

Two O7 runs gave byte-identical output (`shasum` 7c49ef59...). Every number below is copied from the output of these runs.

## Headline

- **O7: confirmed. The soft-score design needs a mitigation before anyone says the outcome is fair.** With today's cardinal scores, a liar gains in **34.7%** of draws (N=3) with an uninformed strategy (score 1.0 on its favourite, 0 on everything else). A liar who has seen the other parties' scores, which a previous public transcript shows, gains in **44.7% / 41.1% / 34.5%** of draws for N=3/4/5 and never loses. That is every draw where a gain was possible. The pre-registered 30% threshold is crossed.
- **O8: confirmed.** One run with the current 500-option cap pins a hidden `cost <= T` threshold to within 1% of the range in **100%** of 2,000 trials. Plain bisection (1 option per run) needs **6 runs**. An option cap does not stop this on its own: 8 options per spec needs 2 runs. Only a budget of **1 run** with a small cap keeps the threshold blurred: K=8 leaves a median error of 27.9 (17.9% of trials still pinned to 1%), and K=4 leaves 49.0 (10.2%). The soft score is a second leak: when a party scales its cost utility to its own budget, **one accepted option reveals T exactly** (98.7% of trials). The verdict also carries the score on red-lined options.

## O7: score shading

### Method

- 5,000 draws per row. Seed 20261025 plus 100·N (the same draws for every strategy at a given N; the sensitivity rows use seed + 7).
- N ∈ {3, 4, 5} parties, 4 to 8 options (uniform), true utilities U[0, 1] i.i.d. Each party bans each option with probability p = 0.2, the red line. The sensitivity rows use p = 0 and p = 0.4.
- Party 0 lies and the rest report truthfully. Red lines are the same in the honest run and the lying run, so only the score moves (except in `fake_redlines`). Liar gain = the liar's **true** utility of the lying-run decision minus its true utility of the honest-run decision. Draws where the honest run deadlocks are excluded; the "agreed draws" column gives the base.
- "Could-gain" = draws where the honest winner is not already the liar's best option that every party accepts. No score strategy can gain outside these draws.
- Strategies:
  - `inflate_fav_zero_rest`: 1.0 on its favourite option, 0 on every other one. Uninformed.
  - `top1_high`: 1.0 on its favourite, true scores elsewhere. Uninformed.
  - `stretch`: rescales its own scores affinely to fill [0, 1]. Uninformed.
  - `bury_honest_winner`: true scores, except 0 on the honest winner when that is not its favourite. Knows the honest outcome.
  - `informed_best_response`: this is our reading of the brief's "mirror others". The liar knows the other parties' scores and the set of options every party accepts; a previous public transcript shows both. It tries targets from its best downward (target 1.0, other all-accepted options 0, the rest 0.5) and keeps the first report that wins.
  - `fake_redlines`: declares every option but its favourite a red line. This is the separate veto attack (F6 attack 2), shown for comparison. It is not a score attack.
- Ordinal variant (a mitigation test): before a verdict leaves, each delegate turns its reported scores into a strict rank normalised to [0, 1]. Ties are broken by the delegate's true utility. A liar can then misreport an order but not a magnitude.

### Results, cardinal scores (current core), p = 0.2

| N | strategy | liar gains | liar loses | could-gain | gains / could-gain | mean gain | honest parties' mean true utility Δ | honest floor Δ | > 30%? |
|---|---|---|---|---|---|---|---|---|---|
| 3 | inflate_fav_zero_rest | 34.7% | 10.1% | 44.7% | 77.7% | +0.064 | -0.060 | -0.093 | YES |
| 3 | top1_high | 0.0% | 0.0% | 44.7% | 0.0% | +0.000 | +0.000 | +0.000 | no |
| 3 | stretch | 7.6% | 1.5% | 44.7% | 16.9% | +0.024 | -0.012 | -0.018 | no |
| 3 | bury_honest_winner | 29.5% | 31.4% | 44.7% | 66.0% | -0.005 | -0.078 | -0.106 | no |
| 3 | informed_best_response | 44.7% | 0.0% | 44.7% | 100.0% | +0.119 | -0.105 | -0.142 | YES |
| 3 | fake_redlines (veto) | 33.4% | 0.0% | 44.7% | 74.6% | +0.142 | -0.122 | -0.162 | YES |
| 4 | inflate_fav_zero_rest | 29.3% | 9.5% | 41.1% | 71.2% | +0.060 | -0.028 | -0.064 | no |
| 4 | top1_high | 0.0% | 0.0% | 41.1% | 0.0% | +0.000 | +0.000 | +0.000 | no |
| 4 | stretch | 8.4% | 0.6% | 41.1% | 20.4% | +0.030 | -0.012 | -0.018 | no |
| 4 | bury_honest_winner | 30.7% | 27.6% | 41.1% | 74.7% | +0.011 | -0.062 | -0.096 | YES |
| 4 | informed_best_response | 41.1% | 0.0% | 41.1% | 100.0% | +0.118 | -0.068 | -0.101 | YES |
| 4 | fake_redlines (veto) | 26.5% | 0.0% | 41.1% | 64.5% | +0.159 | -0.084 | -0.126 | no |
| 5 | inflate_fav_zero_rest | 22.6% | 7.8% | 34.5% | 65.5% | +0.050 | -0.011 | -0.041 | no |
| 5 | top1_high | 0.0% | 0.0% | 34.5% | 0.0% | +0.000 | +0.000 | +0.000 | no |
| 5 | stretch | 8.3% | 0.4% | 34.5% | 23.9% | +0.030 | -0.010 | -0.015 | no |
| 5 | bury_honest_winner | 27.6% | 23.3% | 34.5% | 80.1% | +0.016 | -0.049 | -0.073 | no |
| 5 | informed_best_response | 34.5% | 0.0% | 34.5% | 100.0% | +0.105 | -0.046 | -0.070 | YES |
| 5 | fake_redlines (veto) | 19.9% | 0.0% | 34.5% | 57.6% | +0.149 | -0.054 | -0.087 | no |

Agreed draws: 4,893 (N=3), 4,720 (N=4), 4,484 (N=5). The could-gain share is the "gains" value of `informed_best_response`, and it is the same draw set for every strategy at a given N. `fake_redlines` also causes a new deadlock in 34.7% / 46.8% / 54.1% of draws, when the liar's favourite is unacceptable to another party. When a liar gains, the mean gain is between +0.25 and +0.38 of true utility in every row.

Sensitivity at N=3 (cardinal). With p = 0, the liar gains in **68.1%** of draws, both with `inflate_fav_zero_rest` and with `informed_best_response`; with no red lines the two strategies are the same. With p = 0.4, it gains in 13.9% and 19.2%. Fewer red lines leave more room to shade.

### Results, ordinal (strict-rank) scores, p = 0.2

| N | inflate_fav_zero_rest | top1_high | stretch | bury_honest_winner (gains / loses) | informed_best_response | fake_redlines |
|---|---|---|---|---|---|---|
| 3 | 0.5% | 0.5% | 0.0% | 19.4% / 33.2% | 16.7% | 31.7% |
| 4 | 0.2% | 0.2% | 0.0% | 17.5% / 27.5% | 16.0% | 24.7% |
| 5 | 0.2% | 0.2% | 0.0% | 14.8% / 18.7% | 13.6% | 18.2% |

The full ordinal table with mean gains is in the script output.

### Reading

1. With cardinal scores, an informed liar is close to a dictator over the options every party accepts. It gains in every draw where a gain is possible, at every N, and loses nothing. The mechanism: reporting 0 on every rival drops each rival's floor to 0, so the target's floor is the only one above 0 and wins.
2. Raising your favourite does nothing (`top1_high` = 0.0% at every N). This follows from max-min: if the liar's favourite loses, the liar is not the binding minimum on it. The leverage is in pushing rivals down, not in pushing your favourite up.
3. The honest parties pay for the gain. In the informed case, their mean true utility drops by 0.046 to 0.105 and their floor by 0.070 to 0.142. So the Rawlsian "lift the least-happy" property does not hold for true utilities under strategic reporting.
4. More parties dilute the attack but do not stop it (informed: 44.7% → 34.5% from N=3 to N=5).
5. Ordinal scores remove the uninformed attacks (≤ 0.5%), but an informed liar still gains in 13.6% to 16.7% of draws. That figure is a lower bound, because the search tries one family of rankings, not all of them. Ordinal scores do nothing against fake red lines (18.2% to 31.7%).

### Verdict against the pre-registered threshold

**Threshold crossed.** The liar gains in more than 30% of draws: 34.7% for the uninformed `inflate_fav_zero_rest` at N=3, 44.7% for the informed strategy at N=3, 41.1% at N=4 and 34.5% at N=5. Per the pre-registration, the soft-score design needs a mitigation before anyone says the outcome is fair. The kill condition (gains under 5% in realistic cases) is not met for any informed strategy, even with ordinal scores.

## O8: probing a numeric red line

### Method

- 2,000 trials, seed 20261025. Hidden threshold T ~ U[0, 1000]. The target's red line is `cost <= T`, built with `parley.spec.Constraint`. Each run goes through `run_consensus` with a target and an adversary. The adversary reads the target's `acceptable` bit per option from the transcript, which every party receives as the shared receipt.
- Attack: K evenly spaced costs inside the current interval in each run (K-ary search; K=1 is bisection). Estimate = midpoint of the interval. Success = |estimate − T| ≤ 10, which is 1% of the range.
- Mitigation (a), a cap of K options per spec. For reference, `parley/mcp.py` sets `MAX_OPTIONS = 500` today.
- Mitigation (b), a run budget of B runs. This models "the proposer cannot re-run a spec with changed options without every party's consent".
- Score channel: one option at cost 10, fixed in advance. The adversary inverts the target's soft score, T̂ = cost / (1 − score), for three target utility shapes.

### Results

Runs needed with no run budget:

| options per spec K | runs (median = max) | options queried (median) | success | theory ⌈log_{K+1}(50)⌉ |
|---|---|---|---|---|
| 500 (current cap) | 1 | 500 | 100.0% | 1 |
| 100 | 1 | 100 | 100.0% | 1 |
| 20 | 2 | 40 | 100.0% | 2 |
| 8 | 2 | 16 | 100.0% | 2 |
| 4 | 3 | 12 | 100.0% | 3 |
| 2 | 4 | 8 | 100.0% | 4 |
| 1 (bisection) | 6 | 6 | 100.0% | 6 |

Run budget B × option cap K:

| K | B | pinned to 1% (err ≤ 10) | median error | p95 error | within 10% (err ≤ 100) |
|---|---|---|---|---|---|
| 1 | 1 | 4.0% | 130.8 | 237.6 | 39.0% |
| 1 | 2 | 7.8% | 62.7 | 118.6 | 79.9% |
| 1 | 3 | 15.9% | 31.0 | 59.0 | 100.0% |
| 4 | 1 | 10.2% | 49.0 | 95.4 | 100.0% |
| 4 | 2 | 49.3% | 10.1 | 19.0 | 100.0% |
| 4 | 3 | 100.0% | 2.1 | 3.8 | 100.0% |
| 8 | 1 | 17.9% | 27.9 | 52.8 | 100.0% |
| 8 | 2 | 100.0% | 2.9 | 5.8 | 100.0% |
| 20 | 1 | 42.2% | 12.0 | 22.6 | 100.0% |
| 20 | 2 | 100.0% | 0.6 | 1.1 | 100.0% |
| 500 | 1 | 100.0% | 0.5 | 1.0 | 100.0% |

Score channel, one option at cost 10:

| target utility term | pinned to 1% | median error |
|---|---|---|
| `cost` lower, lo=0, hi=T (own budget as the scale) | 98.7% | 0.0 |
| `cost` lower, lo=0, hi=1000 (fixed scale) | 0.5% | 491.4 |
| no utility (neutral 0.5) | 2.1% | 492.5 |

The 1.3% failures in the first row are trials with T < 10, where the probe option is itself red-lined. Separately, a target with T = 400 returned `acceptable=False score=0.50` for cost 500: **the verdict on a red-lined option still carries the real soft score** (`parley/agent.py` passes `ev.score` whether or not the option is feasible).

### Reading

1. The falsifier row ("recovered within ±10% in under 20 queries") is confirmed by a wide margin. Bisection reaches ±10% of the range in 3 runs of 1 option (100%), and the current cap allows it in a single run.
2. An option cap alone does not help. The total number of options needed stays about log₂(100) ≈ 7 whatever the cap, and the cap only changes how many runs that takes.
3. A one-run budget is the only cheap lever in this model, and it only blurs the threshold. With K=8 and B=1, the median error is 28 (2.8% of the range) and 17.9% of trials are still pinned to 1%. A spec that is not adaptive still leaks about log₂(K+1) bits per numeric red line.
4. The soft score is a bigger leak than the binary verdict whenever a party writes its utility scale relative to its own red line. That is a natural way to write a spec, and `lo`/`hi` are free parameters.

## Honest limits (what these simulations do not show)

- Utilities are i.i.d. uniform and red lines are independent coin flips. Real decisions have correlated preferences, which can make shading easier or harder. Not tested.
- The liar is one party, and the others are honest and do not react. Coalitions, counter-shading and equilibrium play are not modelled. When everyone shades, the outcome may move back toward a different but still unfair point.
- "Informed" assumes the liar has seen the others' scores, for example from an earlier transcript of the same parley or a re-run. In a one-shot run with sealed simultaneous verdicts, only the uninformed rows apply (34.7% / 29.3% / 22.6%).
- The ordinal search is one family of rankings, not exhaustive, so 13.6% to 16.7% is a lower bound on what an informed ordinal liar gets.
- The gain is in the liar's own true utility. The simulation says nothing about whether real owners or LLM delegates would shade. It shows only that the rule rewards shading.
- O8 assumes the adversary can choose option costs freely and that implausible options (cost 487.3) raise no suspicion. Humans who read the list might notice. It models a single numeric red line with a known range; categorical red lines, several attributes and noisy verdicts are not modelled. The B-run budget is a model of a consent rule that does not exist in the code.
- Neither simulation touches what holds independently: red lines are enforced in code, and each owner's replay of their own sheet detects a crossed red line. Those are separate properties, already covered by the tests and probes.

## Wording for grant text

Safe (each part is backed by code, a test or this run):

- "Red lines are enforced in code: an option that crosses any party's red line cannot be chosen, and each owner can replay their own private sheet against the record to check that."
- "Parley does not prevent strategic reporting of soft scores. In our simulation (5,000 random decisions per setting, 3 to 5 parties), a party that misreports its scores after seeing an earlier record improved its own outcome in 35% to 45% of decisions, at the other parties' expense. Hardening the soft-score layer (ordinal scores, sealed simultaneous verdicts) is part of the proposed work."
- "With ordinal-only scores, simple misreporting stopped paying (under 1% of decisions), and an informed misreporter still gained in 14% to 17% of decisions."
- "Binary verdicts leak private thresholds under repeated, adaptive proposals: in simulation, bisection recovered a numeric budget limit to 1% in 6 runs, or in one run with a long option list. Limiting re-runs is part of the threat model work."

NOT safe (contradicted by this run, or unsupported):

- "Parley's outcome is provably fair" / "strategy-proof" / "manipulation-resistant" / "no party can game the result".
- "Max-min guarantees the least-happy party is protected." This holds only for reported scores; under shading, the honest parties' true floor fell by 0.07 to 0.14.
- "Masked verdicts keep red lines private." Each verdict reveals one bit per option, and the score can reveal the threshold itself.
- "Enforced in code" applied to the whole outcome instead of to red lines only.
- "Max-min is provably manipulable", citing Psomas and Verma as a result about Parley's rule. Say "our simulation shows" instead.
- Any number not in the tables above, or a single number without its N and strategy.

## Next options (not built; the rule is not to build ahead of the current Exp)

1. Recommended: write the threat model into the docs and the grant now, using the safe wording above, and file two BACKLOG rows. The first is to stop sending the soft score on red-lined options; the score carries no decision weight there and leaks. The second is a sealed, simultaneous verdict round: commit-reveal, so no party sees others' scores before it commits. Sealing should remove the informed rows (34.5% to 44.7%) and leave the uninformed ones (22.6% to 34.7%); this is inferred from the strategy definitions, not simulated.
2. Alternative: ordinal-only scores in the spec layer. In this run they cut uninformed gains to ≤ 0.5% and informed gains to 13.6% to 16.7%; they do not touch fake red lines. Combined with commit-reveal, the expected residual is near the uninformed ordinal figure (≤ 0.5%). That combination is not simulated yet; it is a one-flag change to `sim_o7_score_shading.py`.
3. Alternative for O8: a per-parley re-run rule (the B budget), plus coarse buckets for numeric red-line attributes in options. Only a one-run budget with a small option list kept the median error above 1% of the range in this model.

## Correction after the mitigation run (2026-10-25, `o7b-mitigation-results-2026-10-25.md`)

Two statements above are weakened by the follow-up simulation (all numbers there from commands, controls matched this file to the last digit):
1. "A sealed commit-reveal round would remove the informed attack" is wrong when the acceptance pattern is public: an informed liar needs only who accepts what, not others' scores, and still gains 44.7/41.1/34.5 percent (N=3/4/5). Commit-reveal alone leaves the uninformed `inflate_fav_zero_rest` at 34.7 percent for N=3 (above the 30 percent threshold).
2. "Ordinal scores cut attacks to under 1 percent" holds only with a tie-break by true utility; with an index tie-break the simple misreport gains 6.2 percent and loses 21.5 percent (still unprofitable).
What does work: ordinal scores plus commit-reveal bring all score attacks below 30 percent (prior-only liar 3.2 to 3.8 percent; acceptance-aware 11.7 to 12.5 percent). Fake red lines are untouched by every scheme. Bounded budgets do not help.
