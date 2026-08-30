# Submission

This is a tested partial construction, not a passing counterexample.

`witness.json` is the evaluator input. `verification.json` contains exhaustive float64 measurements.

| Metric | Measured | Requirement |
|---|---:|---:|
| entropy | 3.03362327271 | >= 3 |
| reverse_kl | 0.805434054607 | >= 0.4 |
| reward_variance | 0.0633323349303 | <= 0.05 |
| gradient_infinity | 0.00379994009579 | <= 0.003 |
| energy_error_per_spin | 0.0253329339131 | <= 0.02 |
| target_sector_mass | 0.491380882635 | >= 0.35 |
| proposal_sector_mass | 0.00028089991938 | <= 0.001 |

Core score: 0.789486129873.

Verification enumerates all 65,536 configurations without probability truncation or renormalization.
The proposal has no biases, is globally spin-flip symmetric, and satisfies every row L1 bound.

Recheck with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B exact.py witness.json`.

Search scripts and logs document the numerical construction. No external sources or delegated agents were used.
