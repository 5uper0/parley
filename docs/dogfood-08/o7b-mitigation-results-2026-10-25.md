# O7b: mitigations for score shading, simulated before anything is built, 2026-10-25

Follow-up to `o7-o8-simulation-results-2026-10-25.md` (O7). That run showed that a party who shades its soft scores gains under Parley's max-min rule. This run tests four candidate mitigations with the same generators, seeds, strategies and metrics. Nothing in `parley/` was changed, and no mitigation is built.

```
.venv/bin/python docs/dogfood-08/sim_o7b_mitigations.py   # ~23 s on 12 cores
```

Two runs gave byte-identical output (`shasum` b6d660da8cad994c38535116843edc4b066872dd). Every number below is copied from that output, except the K=192 check, which was a separate command (see Method).

## Headline

- **Commit-reveal alone does not remove the gain.** The informed attack in O7 never needed the other parties' scores. It needed only the set of options every party accepts. Score 1.0 on the target and 0 on every other all-accepted option, and every rival's floor drops to 0, so the target wins whatever the others report. A sealed liar who knows the acceptance pattern still gains in **44.7% / 41.1% / 34.5%** of draws (N=3/4/5), the same as the unsealed informed liar. A sealed liar who knows nothing gains in **28.9% / 26.6% / 22.2%**, and the uninformed `inflate_fav_zero_rest` attack is unchanged at **34.7% / 29.3% / 22.6%**. N=3 stays above the 30% threshold. O7 predicted that sealing would remove the informed rows; that prediction is wrong whenever the acceptance pattern is known.
- **A score budget (bounded, 1.0 per party) does nothing.** Zeros cost nothing under a budget, and the attack is made of zeros. Informed: **45.4% / 41.4% / 34.8%**. Uninformed: **35.8% / 29.8% / 23.0%**. With commit-reveal and no acceptance knowledge: **29.5% / 26.5% / 22.4%**.
- **Ordinal plus commit-reveal is the only combination tested that removes the gain.** With no knowledge, the liar gains in **3.8% / 3.4% / 3.2%** of draws and loses in 3.9% / 3.5% / 3.2%, a mean gain of **+0.004 / +0.001 / +0.001**. With the acceptance pattern known, it gains in **11.9% / 12.5% / 11.7%** (mean +0.029 to +0.031). That is below the open ordinal informed liar (16.7% / 16.0% / 13.6%) and far below cardinal (34.5% to 44.7%).
- **Price of the mitigation.** When everyone is honest, ordinal scoring lowers the true Rawlsian floor by **0.023 / 0.022 / 0.018**, which is 5.7% / 7.0% / 7.5% of the cardinal floor. Mean welfare rises by 0.003 to 0.008. The decision changes in about 20% of honest draws. For comparison, an informed cardinal liar costs the honest parties 0.070 to 0.142 of floor. Bounded scoring costs less (floor -0.004 to -0.010), but it protects nothing.
- **No mitigation touches fake red lines.** A false red line is a unilateral veto. It pays in **33.4% / 26.5% / 19.9%** of draws (cardinal) and **31.7% / 24.7% / 18.2%** (ordinal), and it creates a new deadlock in **34.7% / 46.8% / 54.1%** of draws under every scheme.

## Method

- Same draw generator as O7: 5,000 draws per row, seed 20261025 + 100·N, N ∈ {3, 4, 5}, 4 to 8 options, true utilities U[0, 1] i.i.d., red-line probability p = 0.2 per party per option. Party 0 lies and the rest report truthfully. Every honest and lying decision is made by the real `run_consensus` over `Agent` delegates. Metrics and the could-gain definition are unchanged; draws where the honest run deadlocks are excluded.
- The script imports `sim_o7_score_shading.py` and reuses its `make_agent`, `to_ordinal`, `lie` (all six strategies), seed, draw count and threshold.
- Each mitigation is a transform the delegate applies to its reported scores before its verdict leaves:
  - `cardinal`: none (the current core).
  - `ordinal_true`: strict rank normalised to [0, 1], ties broken by the delegate's true utility. This is O7's variant, kept as the control.
  - `ordinal_index`: strict rank, ties broken by option index (the lower index ranks higher). This is the variant asked for in (c). It matters only for a liar's tied reports, because honest scores almost never tie.
  - `bounded`: scores clipped to [0, 1], then divided by their sum over the party's own acceptable options, so each party distributes 1.0. An all-zero report becomes a uniform split.
- Commit-reveal is modelled as information: the liar commits before it sees any other party's verdict. `bury_honest_winner` and `informed_best_response` need the realised scores or outcome, so under sealing they are replaced by:
  - `sealed_br_prior`: best response against the true prior. Others' scores are U[0, 1] i.i.d. and others' red lines are Bernoulli(0.2). The liar knows the exact generating distribution, which favours the liar.
  - `sealed_br_acceptance`: the same, but every party's per-option acceptance is known, for example from an earlier masked transcript of the same parley. Only scores are sampled.
  - Both choose, from a fixed family, the report with the highest expected true utility over K = 48 Monte Carlo samples, evaluated through the same transform. The family is: truthful; top-k binary (1.0 on the k best acceptable options, 0 elsewhere, for every k); truthful with one non-favourite acceptable option set to 0; and, when acceptance is known, O7's informed family (target 1.0, other all-accepted options 0, the rest 0.5). Inside the search the liar uses `fast_decide`, a copy of the max-min rule, which the script asserts equal to `run_consensus` on every honest draw. The samples come from a separate per-draw RNG, so the main draws are the same as in O7.
  - K check, N=3, K=192, run separately: cardinal prior 28.8% gains (K=48: 28.9%), cardinal acceptance 44.7% (44.7%), ordinal prior 3.1% (3.8%), ordinal acceptance 11.8% (11.9%). K=48 is enough.
- Uninformed strategies (`inflate_fav_zero_rest`, `top1_high`, `stretch`, `fake_redlines`) use no information about others, so sealing changes nothing for them by construction. Their sealed rows equal the open rows of the same scoring scheme.
- Social cost: everyone is honest, on the same draws. For each scheme the script reports the mean over parties and the minimum over parties of the true utility of the chosen option, averaged over agreed draws. Feasibility does not depend on scores, so every scheme agrees on the same draws.

## Controls

(a) Cardinal, open, reproduces O7 exactly: `informed_best_response` 44.7% / 41.1% / 34.5%, `inflate_fav_zero_rest` 34.7% / 29.3% / 22.6%, with the same agreed draws (4,893 / 4,720 / 4,484) and the same means and deltas in every row.

(d) Ordinal (true-utility tie-break), open, reproduces O7's ordinal table: `informed_best_response` 16.7% / 16.0% / 13.6%, `inflate_fav_zero_rest` 0.5% / 0.2% / 0.2%, `bury_honest_winner` 19.4% / 17.5% / 14.8% gains, `fake_redlines` 31.7% / 24.7% / 18.2%.

## Results: share of agreed draws where the liar gains (loses), p = 0.2

| scheme | strategy | N=3 | N=4 | N=5 | > 30%? |
|---|---|---|---|---|---|
| (a) cardinal, open | inflate_fav_zero_rest | 34.7% (10.1%) | 29.3% (9.5%) | 22.6% (7.8%) | N=3 |
| | informed_best_response | 44.7% (0.0%) | 41.1% (0.0%) | 34.5% (0.0%) | all |
| | fake_redlines | 33.4% (0.0%) | 26.5% (0.0%) | 19.9% (0.0%) | N=3 |
| (b) cardinal + commit-reveal | inflate_fav_zero_rest | 34.7% (10.1%) | 29.3% (9.5%) | 22.6% (7.8%) | N=3 |
| | sealed_br_prior | 28.9% (5.4%) | 26.6% (4.5%) | 22.2% (3.1%) | no |
| | sealed_br_acceptance | 44.7% (0.0%) | 41.1% (0.0%) | 34.5% (0.0%) | all |
| | fake_redlines | 33.4% (0.0%) | 26.5% (0.0%) | 19.9% (0.0%) | N=3 |
| (c) ordinal (index) + commit-reveal | inflate_fav_zero_rest | 6.2% (21.5%) | 5.1% (16.3%) | 3.5% (10.6%) | no |
| | top1_high | 0.5% (0.0%) | 0.2% (0.0%) | 0.2% (0.0%) | no |
| | sealed_br_prior | 3.8% (3.9%) | 3.4% (3.5%) | 3.2% (3.2%) | no |
| | sealed_br_acceptance | 11.9% (2.9%) | 12.5% (1.9%) | 11.7% (1.2%) | no |
| | fake_redlines | 31.7% (0.0%) | 24.7% (0.0%) | 18.2% (0.0%) | N=3 |
| (d) ordinal (true tie-break), open | informed_best_response | 16.7% (0.0%) | 16.0% (0.0%) | 13.6% (0.0%) | no |
| (d') ordinal (index), open | informed_best_response | 17.7% (3.4%) | 16.2% (2.5%) | 14.2% (1.4%) | no |
| | bury_honest_winner | 19.4% (33.2%) | 17.5% (27.5%) | 14.8% (18.7%) | no |
| (e1) bounded, open | inflate_fav_zero_rest | 35.8% (10.2%) | 29.8% (10.1%) | 23.0% (8.2%) | N=3 |
| | informed_best_response | 45.4% (0.0%) | 41.4% (0.0%) | 34.8% (0.0%) | all |
| | fake_redlines | 34.2% (0.0%) | 27.3% (0.0%) | 20.2% (0.0%) | N=3 |
| (e2) bounded + commit-reveal | sealed_br_prior | 29.5% (5.5%) | 26.5% (4.5%) | 22.4% (3.2%) | no |
| | sealed_br_acceptance | 45.4% (0.0%) | 41.4% (0.0%) | 34.8% (0.0%) | all |

`stretch` stays at 7.0% to 8.4% under cardinal and bounded, and 0.0% under ordinal. `top1_high` is 0.0% under cardinal and at most 2.2% elsewhere. The script output has every row with new deadlock, could-gain, gains / could-gain, mean gain, mean gain when it gains, honest mean Δ and honest floor Δ.

### Mean liar gain, and honest parties' true mean Δ / floor Δ

| scheme, strategy | N=3 | N=4 | N=5 |
|---|---|---|---|
| cardinal open, informed_best_response | +0.119; -0.105 / -0.142 | +0.118; -0.068 / -0.101 | +0.105; -0.046 / -0.070 |
| cardinal sealed, sealed_br_prior | +0.085; -0.051 / -0.077 | +0.086; -0.032 / -0.058 | +0.077; -0.022 / -0.041 |
| cardinal sealed, sealed_br_acceptance | +0.119; -0.105 / -0.142 | +0.118; -0.068 / -0.101 | +0.105; -0.046 / -0.070 |
| ordinal sealed, inflate_fav_zero_rest | -0.064; +0.001 / +0.002 | -0.049; -0.001 / -0.001 | -0.031; -0.001 / -0.002 |
| ordinal sealed, sealed_br_prior | +0.004; -0.005 / -0.005 | +0.001; -0.002 / -0.004 | +0.001; -0.002 / -0.003 |
| ordinal sealed, sealed_br_acceptance | +0.029; -0.019 / -0.025 | +0.031; -0.014 / -0.019 | +0.030; -0.011 / -0.014 |
| bounded sealed, sealed_br_prior | +0.085; -0.055 / -0.076 | +0.084; -0.034 / -0.054 | +0.076; -0.023 / -0.038 |
| bounded sealed, sealed_br_acceptance | +0.119; -0.109 / -0.139 | +0.116; -0.070 / -0.097 | +0.104; -0.047 / -0.068 |
| any scheme, fake_redlines (cardinal / ordinal) | +0.142 / +0.134 | +0.159 / +0.143 | +0.149 / +0.136 |

### Fake red lines under every scheme

| scheme | N=3 gains | N=4 gains | N=5 gains | new deadlock (all schemes) |
|---|---|---|---|---|
| cardinal (open or sealed) | 33.4% | 26.5% | 19.9% | 34.7% / 46.8% / 54.1% |
| ordinal (either tie-break, open or sealed) | 31.7% | 24.7% | 18.2% | same |
| bounded (open or sealed) | 34.2% | 27.3% | 20.2% | same |

A false red line removes options outright. Score transforms cannot reach it, and sealing does not stop it because it needs no information about others. The liar never loses with it in this model, but it turns a third to a half of agreed decisions into deadlocks.

### Social cost: everyone honest, same draws

| N | scheme | mean welfare | Δ vs cardinal | mean floor | Δ vs cardinal | decision differs |
|---|---|---|---|---|---|---|
| 3 | cardinal | 0.6067 | | 0.4072 | | |
| 3 | ordinal_index | 0.6097 | +0.0030 | 0.3841 | -0.0231 | 20.4% |
| 3 | bounded | 0.6092 | +0.0025 | 0.3976 | -0.0096 | 12.5% |
| 4 | cardinal | 0.5635 | | 0.3051 | | |
| 4 | ordinal_index | 0.5712 | +0.0077 | 0.2836 | -0.0215 | 20.2% |
| 4 | bounded | 0.5657 | +0.0021 | 0.2987 | -0.0064 | 10.0% |
| 5 | cardinal | 0.5447 | | 0.2385 | | |
| 5 | ordinal_index | 0.5521 | +0.0075 | 0.2206 | -0.0179 | 18.9% |
| 5 | bounded | 0.5459 | +0.0012 | 0.2349 | -0.0036 | 7.4% |

With honest reports, cardinal max-min maximises the true floor by construction, so any other scheme can only lower it. Ordinal trades a 5.7% to 7.5% lower floor for a slightly higher mean.

## Reading

1. The O7 attack is a veto by zeros, not a read of the others' scores. Under cardinal max-min, scoring 0 on every all-accepted rival makes the liar the binding minimum on each of them. What the liar needs is the acceptance pattern, not the scores. That is why `sealed_br_acceptance` equals `informed_best_response` to the decimal, under both cardinal and bounded scoring.
2. Sealing helps only when it also hides the acceptance pattern, and it does nothing for uninformed attacks. A fully sealed cardinal liar still gains in 22.2% to 28.9% of draws, and `inflate_fav_zero_rest` still crosses 30% at N=3.
3. A budget charges for high scores, but the attack is made of zeros, which are free. Bounded scoring moves the attacks that cross 30% (`inflate_fav_zero_rest`, `informed_best_response`, `fake_redlines`) by +0.3 to +1.1 points, so they get slightly stronger. Other rows move by at most 2.2 points.
4. Ordinal scores remove the magnitude of a zero: a buried option still gets rank 0, but the next one up gets 1/(m-1), and the liar cannot put every rival at the bottom at once. With sealing, what remains is close to noise (gains roughly equal losses, mean gain at most +0.004). With known acceptance, about 12% remains, at mean +0.03.
5. O7's ordinal result that simple misreporting gained in "under 1%" of draws depends on the tie-break. With true-utility tie-breaks, a tied liar report falls back to the liar's true order. With index tie-breaks, `inflate_fav_zero_rest` gains in 6.2% / 5.1% / 3.5% of draws and loses in 21.5% / 16.3% / 10.6%, a negative mean gain. It still does not pay, but the "under 1%" figure is not robust.

## Honest limits

- Utilities are i.i.d. U[0, 1] and red lines are independent coin flips. Correlated real preferences are not tested.
- One liar, and the other parties are honest and do not react. Coalitions, counter-shading and equilibrium play are not modelled. Under ordinal plus sealing, several shading parties may still move the outcome.
- The search is not exhaustive. The sealed best response picks from a fixed family over 48 samples, and the open informed liar uses O7's one family. Every gain figure is a lower bound on what a stronger liar gets. The prior liar knows the exact generating distribution, which a real party would not.
- Commit-reveal is modelled as information only. The protocol itself is not modelled: a party that refuses to reveal after seeing the others' reveals (abort-on-reveal) is a new lever, and the rule for a missing reveal (veto, deadlock or exclusion) decides how strong it is. Sealing also holds only within one run. A re-run of the same parley, or any earlier transcript of the same options, hands the liar the acceptance pattern and puts it in the `sealed_br_acceptance` rows. This ties commit-reveal to O8's re-run budget.
- Bounded scoring is one budget variant (normalise over own acceptable options). A budget with a minimum score per acceptable option would charge for zeros and could behave differently. It is not tested.
- The simulation measures whether the rule rewards shading. It does not show that real owners or LLM delegates would shade.

## Wording for grant text

Safe (each part is backed by this run):

- "In simulation (5,000 random decisions per setting, 3 to 5 parties), sealed simultaneous verdicts alone did not stop strategic score reporting. A party that knew which options the others accept still improved its outcome in 35% to 45% of decisions, because the attack needs only that acceptance pattern."
- "Combining ordinal scores with sealed verdicts cut the gain to about 3% to 4% of decisions, with equally frequent losses, when the misreporting party had no prior information, and to about 12% when it knew the acceptance pattern. The cost was a 6% to 8% lower worst-off outcome when every party reports honestly."
- "No score-layer mitigation addresses false red lines. A party that declares false red lines can still veto options unilaterally; this is part of the proposed threat-model work."

NOT safe:

- "Commit-reveal makes Parley strategy-proof" or "sealed verdicts prevent manipulation".
- "Ordinal scores eliminate manipulation." About 12% remains with known acceptance, and the search is a lower bound.
- "A score budget prevents shading." Contradicted by this run.
- Any figure from this file without its N, scheme and liar knowledge.

## Recommendation

1. **Recommended: ordinal plus commit-reveal, with acceptance sealed in the same commitment and a no-re-run rule.** It is the only option tested that brings every score attack below the 30% threshold and the sealed liar's mean gain to about zero. Its price is a 0.018 to 0.023 lower honest floor. File it as one BACKLOG design row for the threat-model work, together with the abort-on-reveal rule and O8's re-run budget. Do not build it ahead of the current Exp. Fake red lines stay a separate, open problem.
2. Alternative: ordinal alone. It needs no new protocol round, and informed gains are 14.2% to 17.7% (index tie-break), below the threshold, at the same honest-floor price. Commit-reveal adds a further cut, to about 12% with known acceptance or about 3% without.
3. Alternative: commit-reveal only. It keeps the cardinal floor intact, but N=3 stays above 30% (`inflate_fav_zero_rest` 34.7%), and nothing improves if the acceptance pattern leaks. It is not enough on its own. Bounded scoring is not a candidate.
