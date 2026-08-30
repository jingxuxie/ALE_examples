# Empirical hardness report

## Concepts and verification modes

| Concept | Mode | Final status | Solvability |
|---|---|---|---|
| 1: compact color-resolved response | A: baseline improvement | solved; not retained as hard | demonstrated |
| 2: guarded weighted-EEC integration | B: counterexample | hard_open_candidate | unknown |
| 3: exact inverse energy flow | C: witness construction | hard_verified_achievable; primary task | demonstrated by private passing witness |

Each concept has **one ratchet, two task generations**. Ten isolated `ultima-alpha` attempts were run; each had a 3600-second budget. Timeout scores use artifacts observed before the strict deadline, not termination-grace output.

## Baseline and champion scores

Scores below are core / worst-family; passing requires the complete task condition, not merely a nonzero score.

| Concept | Original baseline | Original champion | Current baseline / privileged result |
|---|---|---|---|
| 1 | 0.996696 / 0.977350; max tolerance ratio 210.413 | 1 / 1; ratio 0.00124203 | 0.908622 / 0.636015; ratio 9,273,303.98. Current fresh champion: 1 / 1, ratio 0.00220509, 268 scalars. |
| 2 | 0 / 0 | 1 / 1; minimum uncapped margin 1.291893 | Old champion against guard: 0 / 0. Private guarded search best: 0.0679279 / 0.0649429; no passing witness. |
| 3 | 0 / 0; 79/512 lags | 1 / 1; 512/512 lags | Local baseline: 0 / 0, 149/4096 lags; supplied projection baseline: 0 / 0, 99/4096. Private planted witness: 1 / 1, 4096/4096. |

## Fresh-agent scores

| Concept | Generation / attempt | Core | Worst family | Passed | Construction seconds | Diagnostic |
|---|---|---:|---:|---|---:|---|
| concept_1 | 1 / v_1 | 1 | 1 | True | 668.9 | max tolerance ratio 0.0012420287; 268 scalars |
| concept_1 | 2 / v_2 | 1 | 1 | True | 772.2 | max tolerance ratio 0.0022050944; 268 scalars |
| concept_2 | 1 / v_1 | 1 | 1 | True | 971.9 | feasible weight; all numerical reference gates resolve |
| concept_2 | 1 / v_2 | 1 | 1 | True | 994.1 | feasible weight; all numerical reference gates resolve |
| concept_2 | 2 / v_3 | 0.114355473 | 0.114330851 | False | 3600.0 | feasible weight; all numerical reference gates resolve |
| concept_2 | 2 / v_4 | 0.114345822 | 0.114345677 | False | 3600.0 | feasible weight; all numerical reference gates resolve |
| concept_3 | 1 / v_1 | 1 | 1 | True | 710.4 | 512/512 exact lags; SSE 0 |
| concept_3 | 1 / v_2 | 1 | 1 | True | 787.0 | 512/512 exact lags; SSE 0 |
| concept_3 | 2 / v_3 | 0 | 0 | False | 3600.0 | 221/4096 exact lags; SSE 200042 |
| concept_3 | 2 / v_4 | 0 | 0 | False | 3600.0 | 253/4096 exact lags; SSE 139306 |

All final artifacts are schema/constraint-valid; resource scores are 1. Evaluation runtimes are separate from construction budgets and remain in the individual score reports.

## Counterexample search results

- **Compression:** a 60,001-point original-contract sweep passes, but endpoint power-suppressed residual extraction amplifies the original approximation error. The strengthened chart-based generation is solved and passes its broad private sweep. A subsequent local-coordinate bin-integration repair does not change the frozen champion's measured score.
- **Quadrature:** both original agents produce material three-color counterexamples. The nonnested Gauss-12 guard eliminates the old champion. A 1200-configuration private search and both full-hour challengers find no qualifying guarded witness. Independent high-precision refinement and direct source-native confirmation agree.
- **Construction:** exact replay reproduces the original successful projection method. The 17-case scale sweep exposes persistent projection stagnation, including 0/12 successes at larger resolutions in its short screening budget. The current target was fixed before attempts and its private planted event passes every installed constraint. A separate independent evaluator audit passes.

## Substantive capability failures

- **Concept 2:** the fresh agents obtain real error underestimation, but cannot make it sufficiently material in all three color channels while satisfying the fixed smooth-weight and independent-reference contract. Both achieve only about 11.4% of the required margin. Current-target solvability remains unknown; the old-generation witness is not claimed as a current solution.
- **Concept 3:** the agents cannot reconstruct one exact globally consistent high-dimensional discrete energy-flow event from the full two-point correlation within one hour. Feasible approximations and coarse reconstructions do not satisfy the full exact witness condition. Achievability is demonstrated by a private event validated against the same target and constraints.
- **Concept 1:** no surviving substantive failure; the strengthened task is solved and is not retained as hard.
