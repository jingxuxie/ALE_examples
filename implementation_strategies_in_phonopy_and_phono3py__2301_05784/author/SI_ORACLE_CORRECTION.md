# The initial Si failure is not task hardness

The original fitting pilot appeared to fail the diamond family (core 0.4782).
That apparent failure is invalid as hardness evidence.

The public contract explicitly asks for the minimum-Euclidean-norm solution
when a constrained least-squares system is rank deficient. In this input, the
official invariant basis produces a 2304-by-17 joint design of rank 16 and
condition number approximately 1.06e17. The initial author adapter called the
high-level coupled normal-equation solver without validating this assumption.
The installed `symfc/utils/solver_funcs.py` uses LAPACK POSV and discards its
status return. A positive-definite solver is not an adequate oracle for this
rank-deficient public objective.

Both independently installed symfc 1.5.4 and 1.7.3 reproduce the initial target:

| Computation | Training SSE | Real heldout force RMSE |
|---|---:|---:|
| Initial high-level oracle | 646.3432556 | 0.55867895 |
| Fresh participant submission | 0.1812265733 | 0.0070470019 |
| Explicit SVD in official invariant basis | 0.1812265733 | 0.0070470019 |

The submission satisfies every declared invariance at roughly 1e-15. The
directional derivative of the training objective from the old reference toward
that feasible solution is -1292.324058, proving the old reference is not a
minimizer. The explicit design's normal residual is 1.89e-14. The official basis
and its source/version provenance are retained; no invariant-basis algorithm
was invented for this repair.

The original inputs, reference, manifest and pilot scores are preserved for
audit. `manifest_corrected.json` points only the Si case to a separately stored
rank-aware target, with recalibrated baseline metrics. The participant code and
public task are unchanged. Rescoring is not another model attempt or a ratchet.
The primary evidence is `si_audit/runtime.json`, `si_audit/runtime4.json`,
`si_audit/correction.json` and the reproducible `diagnose_si.py` script.

This is an author-reference validity failure, not a demonstrated limitation of
the participant. It must not be used to select or retain the task. The broader
fitting scorer also admits a zero-output shortcut; that independently documented
calibration issue must be resolved before any future retained ratchet is tested.
