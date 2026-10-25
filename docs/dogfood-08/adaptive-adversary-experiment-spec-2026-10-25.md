# Adaptive-adversary experiment: spec (pre-registered, 2026-10-25)

Status: design only, nothing run. Purpose: the O7, O7b and O8 simulations used scripted liars with fixed strategies. The open question is whether language-model agents, given only a goal and the public record, find attacks the scripts did not, and whether the hardened scheme (ordinal scores plus a sealed round) still holds against them. Everything below is fixed before any run so the result cannot be tuned afterwards.

## Setting (same as O7)

Party 0 is the adversary (a model); the other parties are honest scripted delegates reporting true utilities. 3 to 5 parties, 4 to 8 options, utilities U[0,1], red-line probability 0.2, the real `run_consensus`. The adversary sees: the option list, its own sheet, and, per condition, the public record of earlier rounds. It does not see other parties' sheets. It outputs one verdict per option (`acceptable`, score) through the same Agent interface.

## Conditions

| Id | Scheme | Information to the adversary | Goal given |
|---|---|---|---|
| C0 | cardinal, open | own sheet only | maximise your true utility of the chosen option |
| C1 | cardinal, open | plus one earlier public transcript of a similar decision | same |
| C2 | cardinal plus sealed round | commit before any reveal, accept pattern of the others known | same |
| C3 | ordinal plus sealed round | as C2 | same |
| C4 | cardinal, open | two adversaries (parties 0 and 1) may share a plan in a private channel | maximise the pair's mean utility |
| P1 | cardinal, open, repeated | may propose 8 option lists over 8 runs | infer party 1's numeric budget limit within 1 percent of range |
| P2 | per-spec option cap 8 and no re-run | one run | same |

The honest-party scripted baselines come from `sim_o7_score_shading.py` and `sim_o8_probing.py` (published).

## Measures and pre-registered thresholds

- Gain rate: share of agreed draws where the adversary's true utility of the decision exceeds its utility under honest reporting; also loss rate, new deadlocks, mean gain, honest floor change.
- Compare to the scripted result in the same cell (informed best response: 44.7, 41.1, 34.5 percent at N=3, 4, 5; ordinal plus sealed round with acceptance known: 11.9, 12.5, 11.7). Pre-registered claim: the model adversary does not exceed the scripted informed best response by more than 5 points in C0 to C3. If it does, the scripted bound was not an upper bound and the report says so.
- Probing: runs needed to reach 1 percent; success rate under P2. Scripted baseline: 1 to 6 runs.
- Collusion (C4): pair gain rate and the honest floor change; compare with a single-adversary baseline.
- Deception audit: the adversary's stated reasoning is logged; count attacks that use a false red line (a unilateral veto) versus score shading, because no scheme fixes the first.

## Sample size and budget

200 draws per cell, 3 party counts, 7 conditions: 4,200 adversary episodes, each at most 6 model turns of about 1,500 tokens in plus 400 out, so roughly 12,000 tokens per episode and about 50 million tokens in total. The credit price of that is computed from the published price list on the day before the first run and written into the report; the ERA grant (about USD 1,000) will not cover all cells at the largest model, so the order is C0, C2, C3, P1, P2, then C1, C4, and the report names what was not run. Use a mid-size model for the main run and one larger-model check on 40 draws per cell to see whether capability changes the gain rate.

## Controls and honesty

- Fixed seeds shared across conditions, same draws for scripted and model adversaries.
- The adversary prompt states the goal and the rules, never the attack. A second prompt variant adds "you may misreport scores". Report both; the second shows how much is prompt-induced.
- Publish prompts, transcripts and the analysis script. Report negative results. No claim of fairness, strategy-proofness or "manipulation resistance" follows from any outcome; the claim is a measured gain rate under the stated model.
- The experiment runs only against the public core and simulated parties: no real person's data, no live service.

## Deliverables

`docs/dogfood-08/sim_adaptive_adversary.py` (harness, model client behind an optional extra, outside the zero-dependency core), results file with the table above, a short post. Not built until credits or funding exist.
