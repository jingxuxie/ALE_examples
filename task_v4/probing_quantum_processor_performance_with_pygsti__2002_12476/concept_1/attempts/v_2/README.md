# Submitted characterization design

`design.json` is the required static submission: exactly one `batches` field,
containing 840 nonnegative integers in the supplied candidate order.

- Selected circuits: 24.
- Maximum allocation per circuit: 48 batches.
- Total shots: 38,208, in fixed batches of 64.
- Execution cost: 1,599,808 ticks out of the 1,600,000-tick budget.
- No reallocation occurs when circuit records are lost.

## Validation

| Operating points | Overall loss-risk reduction | Worst-regime reduction | Intact mean risk ratio |
| --- | ---: | ---: | ---: |
| Supplied development points | 95.60% | 44.13% | 1.04461 |
| 3,072 additional selection-validation points | 96.05% | 64.19% | 1.07494 |
| 768 independent post-selection holdout points | 95.55% | 70.89% | 1.07428 |

All rows pass the required 50% overall reduction, 30% per-regime reduction,
and 1.20 intact-risk ratio thresholds. The supplied `resilience.risk_profile`
implementation checks all 276 two-circuit loss pairs at every point. The full
14-parameter information matrix retains the two readout nuisance parameters.

`validation.json` records detailed results and the submission SHA-256 digest.
These are local Fisher-information A-risk results, not finite-shot estimator
guarantees or guarantees for every possible operating point.

The accompanying Python scripts and logs document the independent circuit
exchange search, constrained batch allocation, integer rounding, and validation.
Only `design.json` is needed as the submission.
