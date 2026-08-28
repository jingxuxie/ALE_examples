# Verdict: reject the pilot as robustly solved

The frozen solver remains essentially indistinguishable from the input-only strong reference across **nine freshly seeded, scientifically meaningful shifts within the original 20–24-qubit contract**. No reproducible substantive failure region was found. This is evidence to reject this pilot for the intended solution-gap tournament, not a proof that every possible allowed input is easy.

No active task, grading rule, target, participant file, pool, evaluator, reference implementation or frozen submission was changed. All audit artifacts and subprocess staging were confined to this directory. Protected-file hashes match before and after. No fresh agents or new noise models/concepts were launched.

## Results

| Shift | Qubits | Strong reference | Frozen solver | Identification errors |
|---|---:|---:|---:|---:|
| X-sector-only calibration | 20 | 0.999080 | 0.999081 | 0 |
| Y-sector-only calibration | 20 | 0.999063 | 0.999064 | 0 |
| Site-dependent X/Y/Z sectors | 24 | 0.998861 | 0.998861 | 0 |
| Anisotropic connected crosstalk/readout | 20 | 0.996576 | 0.996575 | 0 |
| Additional distance-two crosstalk factors | 24 | 0.998372 | 0.998371 | 0 |
| Non-involutory compiled gates, asymmetric SPAM | 20 | 0.996417 | 0.996416 | 0 |
| High-shot short anchors, low-shot amplification | 20 | 0.997880 | 0.997876 | 0 |
| High-shot amplification, lower-shot anchors | 24 | 0.998601 | 0.998599 | 0 |
| Gate-dependent shot imbalance | 24 | 0.997994 | 0.997996 | 0 |

- Frozen mean: **0.9980933566**; reference mean: **0.9980938966**.
- Frozen worst shift-family mean: **0.9971207729**; worst case: **0.9964158095**.
- Both structural and calibration identification are exact on all cases: zero errors among 2,016 binary identifiability decisions per solver.
- Maximum absolute reference/frozen case-score difference: **0.000003758**.
- Frozen maximum runtime/RSS: **2.93 seconds / 96.44 MiB**. Reference maximum: **33.78 seconds / 420.63 MiB**. Every execution uses the original 120-second/3-GiB Landlock path.

All nine cases qualify under the stronger checks in `PROTOCOL.md`. Both solvers use **identical per-case scales**, computed once from the weak baseline and actual input-only reference run using the unchanged scoring function. The score comparison is not used as the sole reference-validity argument.

## Why the reference qualification is substantive

Across the nine cases, the **minimum** improvement of the reference over the weak baseline is:

- **861.03×** in raw supported-query mean squared error.
- **439.59×** in the public normalized query mean squared error.
- **675.87×** in held-out prediction mean squared error.

At least **120 of 128 held-out means in every case have absolute contrast at least 0.1**. The 95th-percentile expected Fisher prediction standard error is at most **0.01102**, and the corresponding normalized query standard error is at most **0.002672**. Fisher rank matches calibration rank on every case. These are not statistically empty low-signal examples.

The reference's worst absolute prediction RMSE is below **0.00582** and worst normalized query RMSE below **0.001393**. Exact identification is verified independently of the physical rates. A separate integer-Pauli transfer implementation reproduces all 1,008 query rows and 576 sampled circuit rows/signs with zero row discrepancy. Feasible positive-rate displacements in the calibration null space leave all scored query/prediction targets invariant. This explicitly rules out penalizing or rewarding arbitrary planted gauge coordinates.

The unchanged source-validation suite also passes all **14 tests**, including direct density-matrix/Born-rule checks, source-notebook embedding equivalence, independent cycle/cut-space checks, gauge orbits and filesystem isolation. The fresh-case checks supplement rather than replace these tests.

## What the frozen method actually does

Inspection finds a general solution to the declared model, not an ID lookup or a bare pseudoinverse:

1. Signed, bit-packed Clifford propagation and sparse anticommutation/SPAM features reconstruct experiment and query maps from the raw circuit/factor description.
2. A reduced gauge map is derived from shared preparation/measurement factor functions, with constraints imposed when Clifford-transformed generator terms are absent from a gate's declared ansatz.
3. Separate finite-calibration row-space checks distinguish structural identifiability from missing excitation. Equivalent columns and repeated experiments are compressed without changing identifiable outputs.
4. A bias-corrected weighted log fit initializes a constrained **binomial likelihood** fit on the raw counts. The final estimator is not the log-pseudoinverse ablation that failed during author construction.

The method therefore already implements the scientific ingredients supplied by the later gate-set framework. Rotating calibration sectors, changing connected crosstalk supports, using non-involutory compiled Clifford gates, removing correlated preparation factors, or reallocating shots does not defeat it. Sparse/vectorized implementation explains its speed advantage over the author's dense/reference loops; the longer reference runtime is not evidence of participant hardness.

## Ratchet decision and scope

**No focused original-domain ratchet is justified by this audit. Reject this concept as robustly solved by a general source-model method.** Adding low-signal data, changing a clerical ID, grading a gauge-dependent coordinate, or merely enlarging a dataset would not establish the missing scientific bottleneck and is not proposed.

The audit deliberately stops at the original 20–24-qubit contract. **No 40–64-qubit exploratory cases were run**, and no extended-scale robustness or failure is claimed. A future extension would need an explicitly revised domain and an independently feasible reference; it cannot retroactively establish an original-domain counterexample.

The nine cases test the listed regions, not every local ansatz, compilation or acquisition design. In particular, informative short-to-moderate held-out compositions were retained to exclude meaningless low-signal failures. The existing pilot already tested the original deeper holdouts. The conclusion is bounded empirical rejection of this task candidate, not a theorem about all quantum-noise learning.

## Artifacts and reproduction

- `PROTOCOL.md`: predeclared shifts and qualification rules.
- `run_audit.py`: fresh input generation, independent checks, unchanged evaluator execution, preservation checks.
- `summarize_audit.py`: independently recomputed raw-query improvements and aggregate verdict statistics.
- `summary.json`: complete nine-case results, raw losses, identical scales, Fisher diagnostics, resource measurements and qualification flags.
- `cases/*/`: unlabeled audit input, private scoring oracle, actual reference/frozen output, and per-case result.
- `independent_source_tests.log`: all 14 unchanged source/physics tests passing.
- `preservation_before.json`, `preservation_after.json`: matching protected-artifact hashes.

From this directory:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B run_audit.py --resume
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B summarize_audit.py
```

Omit `--resume` to regenerate and execute all nine frozen cases again; this writes only audit-local artifacts. `--case NAME` replays one predeclared case. No active-pool promotion or task modification is performed.
