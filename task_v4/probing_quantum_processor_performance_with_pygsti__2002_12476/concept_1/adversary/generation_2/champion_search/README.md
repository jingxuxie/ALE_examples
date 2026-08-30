# Private generation-2 champion stress and feasibility search

This directory is generation-time work, not a fresh-agent attempt. It must not
be exposed to later participants. All sidecar writes are confined to this
directory. The completed generation-2 champion and completed v2 solver were
authorized inputs; no active v3 or concept-2 attempt was inspected. Older
portfolio artifacts and the champion remain unchanged.

## Objective and evidence boundaries

The engineering objective selected by main is a worst-three-selected-circuit
loss mean at most four times the actual champion's intact mean, a loss mean at
most five times that champion's intact mean in every family, and an overall
intact mean at most 1.20 times the champion's. Equivalently the inverse-inflation
scores must exceed 0.25 overall and 0.20 in every family. Physical cost, batch,
and cardinality constraints remain unchanged. No passing proof is asserted by
the search logs. The final official evaluation and `final_report.json` determine
the reported outcome.

The earlier provisional 50%/30% relative reductions were too weak: two old
private designs passed those relative thresholds while missing the engineering
caps substantially. `legacy_relative_reduction_diagnostic` fields are retained
only for diagnosis and are not evidence of passing the frozen task.

Private optimization first used the archived 60-point benchmark, then that
benchmark plus 180 newly generated points (30/family, seed 735046610). The
archived benchmark is copied to `training_source.npz`, SHA-256
`60badd3b879b99b397293e670a823980b5f9f134450edd305f328b6f831d6e38`.
The final training set therefore contains 240 points. Main's new 600-point
benchmark, seed 83170246915, was not read or used for fitting. A final official
evaluation is permitted only after optimization stops; there is no subsequent
fit to its feedback. Main's authorized participant/evaluator changes are not
changes by this sidecar.

## Final held-out result: feasibility unknown

After fitting stopped, the frozen `final_design.json` was evaluated once by
the current official evaluator on main's 600-point benchmark. It is physically
valid: 24 circuits and 1,599,360/1,600,000 execution ticks. Its exact scores are:

- Core: **0.06984391375378864**, below 0.25.
- Worst family: **0.03942085073822282**, below 0.20 (anisotropic).
- Intact ratio: **1.2000974829139808**, narrowly above 1.20.
- Mean worst-three-loss A-risk: **70.99778229269543**.
- Overall triple-loss risk reduction relative to the champion: 99.8893%.
- `valid=true`, **`passed=false`**. No passing proof was found.

The overall and worst-family risk caps are missed by factors of approximately
3.58 and 5.07, so this is not just an intact-guard rounding issue. The candidate
was not repaired or refitted after this held-out result. On the independent
240-point private training set its core/worst/intact scores were
0.07142559332669438 / 0.04130680496757265 / 1.1905216104746266. The slightly
worse held-out intact score is an observed generalization effect, not a reason
to relax the frozen guard. A finite unsuccessful search is not an
infeasibility proof. The frozen target's achievability remains **unknown**.

## Broad stress result for the actual champion

Final stress scores enumerate every selected pair and triple with independent
dense information-matrix inversions. Maxima are taken separately at each
operating point before averaging. These are local Fisher A-risks, with nuisance
parameters marginalized, not finite-shot empirical estimation errors.

| Private ensemble | Points | Intact mean | Worst-pair mean | Worst-triple mean |
| --- | ---: | ---: | ---: | ---: |
| Archived training | 60 | 5.000974 | 10.564595 | 81,142.259 |
| Broad sampler draws | 3,000 | 4.917090 | 9.990030 | 100,059.914 |
| Independent private confirmation | 600 | 4.923185 | 9.993346 | 112,359.172 |

The private confirmation seed is 627018399, not main's new benchmark seed.
The broad maximum triple-loss risk is 26,881,850.740. The top 1% of operating
points contribute 49.51% of the total triple risk. Pair risk remains stable.

| Family, broad 3,000 | Champion intact mean | Pair-loss mean | Triple-loss mean |
| --- | ---: | ---: | ---: |
| anisotropic | 6.016110 | 14.579253 | 210,426.462 |
| detuned | 4.007813 | 6.987605 | 4,953.955 |
| long_coherence | 3.582747 | 6.778516 | 24,837.183 |
| mixed | 6.329772 | 13.883668 | 5,308.294 |
| near_nominal | 3.980304 | 7.403101 | 162,908.495 |
| readout | 5.585796 | 10.308036 | 191,925.097 |

The exact aggregate/family inflation, quantiles, worst triples, circuit
definitions, and parameter-variance increments are in `*_scores.json`,
`*_roots.json`, and `champion_diagnostics.json`.

## Root-cause clusters and scientific cautions

The dominant triple is [461, 471, 476], exposing the Y_z coherent-error
direction. It is worst on 52/60 archived points and 2,616/3,000 broad points,
contributing about 80,346 to the archived overall mean risk increase. A second
cluster [139, 320, 353] exposes X_z;
a smaller [185, 207, 278] cluster exposes the Y depolarization rate.

At zero coherent error, the only champion circuits with nonzero Y_z Fisher
coordinate are exactly 461, 471, 476. Removing them makes the remaining Y_z
column identically zero at finite-difference steps 1e-5, 1e-6, and 1e-7. The
smallest remaining singular value is 5.82e-16. Risk then scales inversely with
the numerical ridge: approximately 1e8, 1e10, and 1e12 for ridges 1e-8, 1e-10,
and 1e-12. This is local first-order nonidentifiability, not a demonstrated
failure of all nonlinear finite-shot inference methods.

432 additional in-support boundary points scale coherent errors toward zero,
leaving rates and readout parameters unchanged. This changes sampling density
and is a stress test, not another unbiased Monte Carlo mean. Triple risk grows
from about 88,935 at scale 1 to about 1e10 at scale zero. Rank-three updates can
lose about 1.37e-4 relative accuracy at that ridge-dominated boundary; all
reported boundary values use dense inversion instead.

Stratified empirical bootstraps of the 3,000 broad points show triple-mean CV
1.078 for samples of 60 and 0.322 for samples of 600, versus pair-mean CV 0.0535
and 0.0168. These describe this finite empirical distribution, not a proof of
population moments. They support main's larger benchmark and caution against
small-ensemble tail claims.

After repairing the primary coherent-error weakness, private pilot designs
shift the largest losses toward I and X depolarization information. For the
phase-2 pilot, [59, 278, 736] and [59, 185, 263] dominate. Improving those rate
directions competes with the intact-efficiency guard, short-circuit shot caps,
and the 24-circuit support limit. This is an observed search obstruction, not
a lower bound proving infeasibility.

## Search and numerical validation

The runnable private search combines continuous epigraph SLSQP batch
allocation, full-model analytic gradients, integer budget repair, single and
double support exchanges, and physically classified rate-probe exchanges.
Cheap screening uses family-balanced private subsets; full candidate selection
enumerates all triple losses. `search.jsonl` and phase-specific logs preserve
the search trajectory. Earlier designs/scores remain as `phase_*` snapshots.

`numerical_checks.json` reports rank-three versus dense relative errors of
2.30e-10 for the champion and 1.13e-12 for a pilot on the archived 60 points;
independent reconstructed solves agree to 2.94e-12 and 5.31e-14. The analytic
guard-gradient finite-difference check has maximum normalized error 1.21e-6.
These checks passed. Broad champion rank-update error reaches 9.27e-9, still
small away from the deliberately singular boundary cases.

From the concept root, examples of reproducible private commands are:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
/usr/bin/python adversary/generation_2/champion_search/diagnostics.py
/usr/bin/python adversary/generation_2/champion_search/numerical_checks.py
/usr/bin/python adversary/generation_2/champion_search/final_search.py --seconds 290
/usr/bin/python adversary/generation_2/champion_search/audit.py --submission final_design.json --prefix final_ --datasets hidden broad confirmation
/usr/bin/python evaluator/evaluate.py --submission adversary/generation_2/champion_search/final_design.json --output adversary/generation_2/champion_search/official_score.json
```

The optimizer examples are for independent reruns, not permission to resume
fitting after seeing the held-out official score. `final_design.json` is the
immutable end-of-search candidate, `official_score.json` is its one final
current-evaluator score, and `final_report.json` records feasibility honestly.
