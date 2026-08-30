# Hardness-discovery report

## Concepts, scores, and decisions

Compiler scores are mean / worst-family cost reduction (higher is better). Calibration scores are mean / worst-family NRMSE (lower is better).

| Concept and verification mode | Baseline / prior champion | Fresh ultima-alpha result | Ratchets | Final status | Solvability |
| --- | --- | --- | --- | --- | --- |
| 1. Hardware-aware phase compilation — A, baseline improvement | Baseline 0% / 0%; prior champion on ratchet suite 75.11% / 73.44% | 80.84% / 80.32%; target 82% / 80%; 32/32 valid | 1 | hard_open_candidate | Generic passing compiler unknown |
| 2. Native-CX linear synthesis — C, witness construction | Weak baseline 0/4; private feasible witness 4/4 | 2/4 accepted; all four exact and within CX-count caps | 0 | hard_verified_achievable | Demonstrated |
| 3. Adaptive cross-resonance calibration — E, active experiment design | Baseline 0.07761 / 0.11499 | 0.03597 / 0.05712; target ≤0.060 / ≤0.090; 32/32 valid | 0 | solved | Demonstrated by fresh champion |

There were four isolated fresh-agent attempts, each limited to one hour. The first compiler attempt passed its original 40% / 25% target with 63.57% / 58.69%, before the private ratchet. The witness attempt exhausted its hour; the other three completed normally.

## Counterexample searches

- Compiler: 96 broad cases, 24 initial basis-barrier cases, then 32 focused cases exposed 32 certified cost gaps in the first champion. Exact private construction circuits reach 82.88% mean reduction on the focused suite, but are not a general compiler. This justified the single ratchet; thresholds were frozen before the new fresh attempt.
- Compiler challenger: an additional 64 independently seeded, headroom-filtered workloads missed the unchanged target, scoring 80.30% mean / 80.16% worst-family reduction. These were generated before the challenger score was observed and never provided to it.
- Native-CX witness: no full-task passing fresh champion existed, so no ratchet was required. Independent dense-matrix and dependency-DAG checks validate all four private witnesses and reproduce both fresh depth-cap failures.
- Calibration: 128 broad episodes, 72 independent-noise repeats, and a 64-episode continuous-neighborhood/frame audit produced no trustworthy aggregate or resource failure. One noisy point did not generalize into a failing regime. No artificial harder generation was created.

## Substantive failures and final selection

- Compiler: exact semantics and runtime compliance succeeded, but hidden workload quality remained 6.07% short in the further reduction needed from its remaining normalized cost. Maximum case runtime was 12.92/15 seconds. The failed capability is budgeted shared-parity/common-basis synthesis that generalizes beyond public workloads; passing generic solvability remains unknown.
- Native-CX witness: the fresh artifact reached count/depth 218/81 on the 30-qubit target and 255/85 on the 34-qubit target, versus caps 227/78 and 261/79. Private feasible artifacts achieve 214/72 and 246/73. The failed capability is jointly discovering a low-count native factorization and enough duration-aware parallelism, not correctness or output formatting.
- Calibration: no capability failure was established at the fixed target; the fresh adaptive controller solved it and survived the broader audits.

**Selected task: concept_2. Final status: hard_verified_achievable.** Concept 1 is additionally retained as hard_open_candidate; concept 3 is recorded as solved, not claimed hard.
