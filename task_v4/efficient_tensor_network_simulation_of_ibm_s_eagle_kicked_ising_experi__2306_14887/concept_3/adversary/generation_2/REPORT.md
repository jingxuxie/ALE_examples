# Generation-two private challenge: No champion failure found

The exact v2 frozen submission was copied, not moved, into `champions/generation_2`.
The unchanged trusted evaluator reproduces fidelity **0.952414470917496**, core **0.968402559115180**, and a valid pass on 223 original frozen cases.

## Model tested

All current graph, 24-layer pulse constraints, gain and ZZ ranges, and target 0.95 remain unchanged.
The proposed model assigns a separate time-static 12-site RZ-angle vector to each of the two alternating bond matchings.
Each component remains in [-0.01, 0.01] radians per site per layer. After each layer's ZZ and RX gates, apply the corresponding matching's RZ field, including after layer 23.
Equal even/odd vectors exactly recover the current static model. This is not independent shot noise or arbitrary per-layer noise.

## Coverage and results

- 751 static records: the original 223, 16 previously reported difficult cases rechecked independently, and 512 newly seeded corner/interior cases.
- 2,914 proposed-model structured and random cases: 1,350 amplitude-plane, 540 cross-spatial-pattern, 512 random vertex, and 512 near-boundary cases.
- 384 cyclic spatial-offset/sign cases at 16 prior difficult calibrations.
- 64 exact-adjoint continuous adversarial restarts in all 39 calibration coordinates, using 6353 objective/gradient evaluations.
- Rank 8,388,608 sign corners modulo simultaneous sign inversion with a quadratic surrogate at 17 calibrations; check the top 48 each using exact dynamics (816 exact confirmations). The huge surrogate count is **not** an exact exhaustive robustness check.
- Combined saved endpoint records: **4929**, representing **4494 unique exact calibrations**; **0 failures**.
- Worst compiled fidelity **0.951877877712868**, independently confirmed **0.951877877712861**.
- Worst genuinely unequal matching-field fidelity **0.952148280586491**.

## Observed weakness, not a failing cluster

The lowest found point is in the old equal-vector static subcase: both RX gains -0.025, ZZ common -0.015, every edge residual -0.005, and the same structured +/-0.01 spatial field for both matchings. Its cat-basis population is 0.952071183318, relative cat phase -0.003293173 radians. The measured loss is mainly leakage outside the two cat-basis states, not a large GHZ relative phase.
Uniform opposite-matching drift is less harmful than uniform equal drift in the initial probes. Independent spatial patterns, cyclic offsets, continuous searches, and quadratic-ranked local sign patterns have not exposed a new matching-specific failure. This is evidence about tested points, not a proof that every unequal matching field is easier.

## Private feasibility comparisons

All 16 period-four simultaneous-pi branch patterns preserve nominal zero-calibration fidelity to roundoff. The 15 nontrivial patterns have small-training-set minima between 0.724168963540 and 0.870257621807, below the original champion's 0.951877877713. They worsen calibrated robustness without further redesign.
- Continuous refinement starting from `unmodified_champion`: minimum 0.919226135216 on 4113 saved cases; 1021 below target.
- Continuous refinement starting from `best_nontrivial_period_four_branch`: minimum 0.813718888791 on 4113 saved cases; 2490 below target.
These are deliberately bounded, small-training-set comparisons, not evidence of impossibility. They demonstrate that nominally equivalent branch changes and local refinement need independent broad validation. All private pulses remain in this adversary directory; nothing is exposed to the next participant.
The archived champion itself already provides a passing witness for every proposed-model case tested here.

## Audit and disposition

The compiled all-4096-amplitude simulator is checked against independent tensor-axis gate contractions, not participant code. Maximum fidelity discrepancy 6.33e-15; pulse-gradient finite-difference error 1.35e-09; calibration-gradient error 6.65e-10. Equal-field reduction agrees with the current trusted checker within 2.22e-15. No nonzero-drift parity invariant is imposed.
Integrity audit: 241 protected files and 87 champion/source files checked; passed = True.
**Do not promote a matching-only final ratchet on this evidence:** no separating failure was found. No claim of continuum robustness is made. Live participant, evaluator, hidden suite, status, freeze, and original attempts remain unchanged.

## Reproduction

From the concept_3 directory, compile `adversary/generation_2/statevector.cpp` using `g++ -O3 -std=c++17 -fPIC -shared` with output `adversary/generation_2/statevector.so`.
Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python adversary/generation_2/reproduce.py --case adversary/generation_2/lowest_tested.json`.
Use `lowest_genuinely_matching_dependent.json` for a case outside the old equal-field model. `physics.py` reruns simulator and gradient audits; `challenge.py`, `quadratic_corners.py`, and `variants.py` regenerate private search evidence. These scripts never run fresh-model calls or modify the live task.
