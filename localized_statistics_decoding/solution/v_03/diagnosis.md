# Recovery-stage diagnosis

The legacy stage is a valid binary solver but is not a reliable decoder. It
chooses one reliability-ordered affine representative and does not revisit
bad basis decisions or explore alternative low-cost sectors. On both curated
public batches it achieves 100% syndrome consistency but 0% logical recovery.
This is not a defect in its parity arithmetic; a more consequential search is
needed. Treating the frontend LLRs as calibrated independent evidence would
compound its failure.

The final implementation uses several iterative-message schedules and scaling
choices, higher-order ordered-statistic candidate searches, and final selection
by the physical independent-mechanism likelihood. It retains the baseline
candidate, explicitly verifies every candidate's syndrome, and accepts quantum
equivalence through the supplied logical map instead of exact fault-vector
matching. Different schedules can escape different trapping configurations;
single-representative inversion is the tested inferior approach.

The local native kernel is vendored within this solved workspace. Runtime uses
only local code/binaries and the declared numerical runtime, with no network,
installation or access to another workspace. The reference is intentionally
not a minimal implementation. The behavioral evaluator does not require its
specific search family, message updates, parameters or candidate vectors.

Measured baseline -> final public performance:

| Case | Syndrome fraction | Logical recovery | Mean candidate cost | Runtime seconds |
|---|---:|---:|---:|---:|
| validation_small | 1.0 -> 1.0 | 0.0 -> 1.0 | 50.9166 -> 23.1506 | 0.178 -> 0.405 |
| validation_large | 1.0 -> 1.0 | 0.0 -> 1.0 | 105.4079 -> 56.0985 | 0.229 -> 1.055 |

Executed from the task root with OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1:

```
python authoring/validate_v03_reference.py
python evaluator/v_03/evaluate.py --submission solution/v_03
```

The validation wrapper runs both the original and replacement CLI on both
public networks and calls the supplied diagnostic comparator. The final
outputs are saved as validation_small_predictions.npz and
validation_large_predictions.npz. These rates describe a curated debugging
corpus, not an unbiased channel error rate or a code threshold. The search does
not certify exact maximum-likelihood sector decoding on arbitrary inputs.
