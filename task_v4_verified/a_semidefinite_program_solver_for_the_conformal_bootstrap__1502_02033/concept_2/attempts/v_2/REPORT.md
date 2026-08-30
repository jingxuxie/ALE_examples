# Final submission

## Outcome

The witness passes 0 of the three public profiles. The requested falsification was not achieved.

`witness.json` is the final data artifact. It satisfies the algebraic contract and the exact negative-evidence threshold, as checked by `validate.py`. No claim of successful screening evasion is made unless `passed` is true in `submission_summary.json`.

## Exact evidence and constraints

- Degree: 24.
- Common denominator: 1000000000000.
- Rational witness point: `613841/715746`.
- Normalized Rayleigh quotient: approximately -1.020009926980229e-07; the full exact reduced fraction is in `exact_validation.json`.
- Minimum diagonal at the witness: 0.02672569656180986.
- Minimum principal two-coordinate determinant: 1.138628722044055e-05.
- Squared commutator Frobenius norm: 0.0418430832277943.
- Largest coefficient row-sum bound: 3.386727031136, below four.
- Artifact size: 5074 bytes.

## Reproduction

From this output directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python validate.py witness.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python ../../participant/workspace/guard.py witness.json
```

`public_guard_report.json` contains the unmodified public screen's profile reports. `submission_summary.json` records the outcome without treating admissibility as success. `candidate_comparison.json` records the final comparison of admissible saved candidates.

## Investigation and scratch work

All search code and generated data are local to this output directory; participant assets were used read-only. The searches use single-threaded BLAS and the public guard imported from the participant assets.

The investigation covers the supplied coupled-branch baseline, sparse and dense low-rank Gram constructions, optimized local coordinate geometries, quartic branch clustering, paraunitary-filter rank-two polynomial matrices, unimodular congruences, bounded coefficient perturbations, and differential-evolution refinements of filter constructions. The `*_search.py`, `optimize_*.py`, and `*.log` files retain these experiments. `diagnose.py` separates candidate locations by principal minor. `finalize.py` selects the best saved admissible candidate by profiles accepted, then by the worst value across the shared candidates and all fixed meshes.

Final candidate source: `mix_best.json`.
