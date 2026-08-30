# Hardness discovery report

## Concepts and verification modes

- C1: sample-specific dynamical-fraction prediction — D, hidden prediction.
- C2: spectrally matched disorder layouts — C, witness/design construction.
- C3: robust spectral-window counterexample — B, counterexample/falsification.

## Baseline and fresh-agent scores

Scores are core / worst family. C1 uses RMSE (lower is better; targets 0.035 / 0.050). C2 uses normalized constraint scores (100 / 100 and every condition must pass). C3 uses signed discrepancy (targets 0.060 / 0.050 plus base and coverage constraints). Each generation has two isolated ultima-alpha attempts with a one-hour limit.

| Concept / generation | Mode | Baseline | Fresh attempts |
|---|---|---|---|
| C1 g1 | D | 0.036780 / 0.043904 | v1: n/a / n/a (fail); v2: 0.018166 / 0.020573 (pass) |
| C1 g2 | D | 0.039969 / 0.044421 | v3: 0.019052 / 0.021652 (pass); v4: 0.019729 / 0.022105 (pass) |
| C2 g1 | C | 21.663848 / 17.690913 | v1: 80.272377 / 54.220328 (fail); v2: 83.418942 / 59.477835 (fail) |
| C3 g1 | B | 0.008670 / 0.006030 | v1: 0.063976 / 0.057290 (pass); v2: 0.062582 / 0.058670 (pass) |
| C3 g2 | B | 0.004549 / 0.001231 | v3: 0.059177 / 0.057339 (fail); v4: 0.072975 / 0.064001 (pass) |

C1 g1 v1 exceeded the 3-second inference budget at 3.005s and has no accuracy score; it is not used as evidence of scientific hardness. C2 v1 and C3 g2 v3 were stopped at the one-hour deadline and their stable, valid checkpoints were scored.

## Champion and privileged scores

- C1 g1: fresh v2, 0.018166 / 0.020573, 1.674s evaluation.
- C1 g2: fresh v3, 0.019052 / 0.021652, 1.010s evaluation.
- C2 g1: privileged portfolio, 100.000000 / 100.000000, 25.300s evaluation.
- C3 g1: fresh v1, 0.063976 / 0.057290, 3.011s evaluation.
- C3 g1: privileged witness, 0.063160 / 0.058753, 3.649s evaluation.
- C3 g2: fresh v4, 0.072975 / 0.064001, 14.431s evaluation.
- C3 g2: privileged witness, 0.060148 / 0.058932, 10.559s evaluation.

## Counterexample search results

- C1 g1: a 1,760-realization private bank exposed L14 size-transfer failure. Merely fixing unsupported-size dispatch still gives RMSE 0.058231 / 0.072183; the raw unsupported-size failure is not treated as scientific evidence. Generation 2 supplies new L14 public data and keeps the numerical targets fixed.
- C2: 1,800 privately searched layouts and 240 robust pairs did not initially yield a complete design. Recombining 71 cached bank-two layouts over 5,041 ordered pairs finds two passing pairs. A three-bank portfolio passes every requirement; independent full-spectrum LAPACK verification agrees within 4.86e-13. Both fresh designs meet all relaxation-separation conditions, but respectively miss spectral matching in seven and five of nine families.
- C3 g1: both fresh witnesses pass their initial grader, but the best-core champion passes 0/16 independent replication banks (mean core 0.049581); the earlier v2 champion also passes 0/16. Both fail the frozen generation-two bank. Generation 2 uses separate, independent 128-probe calibration and grading banks, with unchanged numerical thresholds.
- C3 g2: privileged scale search tests 30 candidates and finds one passing witness; an independent LAPACK driver agrees within 4.62e-13.
- C1 final champion stress: The best generation-two champion passes both independent 320-case replication batches. Pooled RMSE is 0.017793 overall / 0.020054 worst family on 640 new L14 realizations, with inference times 0.690s and 0.579s. No aggregate, family, or resource failure remains under the stated objective. Isolated pointwise residuals are not converted into an undisclosed maximum-error requirement.
- C3 final champion stress: The generation-two champion passes 16/16 independent 128-perturbation banks (2,048 new perturbed profiles), mean core 0.070309, minimum core 0.063668, and minimum worst-family 0.052194. No residual valid failure is found under the disclosed family laws. No arbitrary threshold or out-of-contract requirement is introduced to manufacture hardness.

## Ratchets and final status

- C1: 1 ratchet generation(s); `solved`; solvability demonstrated.
- C2: 0 ratchet generation(s); `hard_verified_achievable`; solvability demonstrated.
- C3: 1 ratchet generation(s); `solved`; solvability demonstrated.

## Substantive capability failure

Retained C2 is `hard_verified_achievable`: neither fresh agent constructs a fully valid robust design, while the privileged portfolio does. The failure is selecting spatial arrangements that preserve a field histogram and keep adjacent-gap statistics matched across unseen perturbations while maintaining a large dynamical separation. It is not a format failure, missing implementation formula, or numerical-precision artifact.
