# Adaptive correlation-energy policy

Run `python3 solution.py` in this directory. Input and output follow the supplied
JSON-lines contract. NumPy and SciPy are the only nonstandard runtime dependencies.
`SUBMISSION_FILES.txt` lists the seven files required for deployment. All other
files are construction experiments, training caches, or validation reports.

## Policy

1. Observe every three-virtual CAS energy, using 56 cost units.
2. Use the measured signed increments to form a covariance model for unobserved
   higher-order increments. Evaluate six-virtual anchor choices together with
   their affordable follow-up queries, then select a design costing at most the
   remaining 104 units.
3. Condition the full-energy estimate on all queried energies. For systems with
   appreciable remaining uncertainty, fit a small, three-component response
   model to the observed increments. Use its higher-order correction only when
   the fit passes a quantitative residual check.
4. Bound optional fitting by the persistent process's cumulative CPU use.
   Numerical fitting failures revert to the covariance-based estimate.

The policy does not use the family label or access participant assets at runtime.
It does not query seven- or eight-virtual spaces. The response model is an
approximation to the effective paired-electron system, not a molecular integral
reconstruction.

## Validation

The supplied 36-system practice runner reports:

- Overall RMSE: **6.2804 microhartree**.
- Worst-stratum RMSE: **12.2415 microhartree**.
- Maximum query cost: **160**.
- Valid protocol; the practice accuracy and budget targets pass.

See `practice_report.json` for individual records and `practice_run.log` for the
summary. `validate_suite.py` additionally exercises a persistent 120-system run
using generated ordinary, stronger-coupling, and signed-cancellation examples;
its report is `synthetic_validation_report.json`. These generated tests are not
the unavailable hidden evaluator, and practice results do not certify hidden
accuracy.

Construction uses only the supplied practice assets, the supplied model code,
and the local NumPy/SciPy runtime. The neural and alternative response models
in the experimental files are not dependencies of the submitted policy.
