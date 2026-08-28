# Witnessed performance evidence: pilot04

## Resource isolation

Actual numeric affinity: CPUs **382–383**; one BLAS thread; no fresh agents or participant solver launch. All writes are in this performance directory. Dense children had a **6 GiB address-space cap**. Direct search used at most two 2 GiB workers and a 1 GiB-soft-limit parent; its 6 GiB hard ceiling only permits children to establish their own limits.

## Dense witnesses

- Actual full **15,860 × 15,860 complex128** Hamiltonian, 3.7482 GiB for one dense matrix.
- `numpy.linalg.eigh`: **allocation_failure** in 0.817 s total. Actual exception: `Unable to allocate 3.75 GiB for an array with shape (15860, 15860) and data type complex128`. This is allocation failure during the eigensolver entry, not evidence of a completed numerical kernel.
- In-place SciPy `evr`, selecting eight central eigenvalues: **wall_timeout**, still inside the eigensolver at its 60 s whole-process watchdog. This does **not** establish a 1200-second timeout. Its resource fields are the last persisted pre-call snapshot, not a measured final peak RSS.

## Actual direct-forward optimization

A two-parameter, first-improvement coordinate search starts from the supplied original zigzag. It does not read the archived optimizer or optimized masks. All completed candidates use 51 momenta × three exact robustness points and independent topological checks; using the exact private points favors this baseline. Search updates use only its newly measured robust gaps. The reference scalar is read after search stops.

Wall time **1200.26 / 1200 s**; numeric-child CPU **1731.98 s**. Best robust gap **0.119021791570 meV**; weak **0.082046466446**, stored strong **0.182179596386 meV**. Unbounded normalized single-family core: **0.36926165**.

| Candidate | Amplitude / width (nm) | Full 3×51 | Feasible | Wall s | Robust gap meV | Normalized core |
|---|---|---|---|---|---|---|
| 0 | 100 / 200 | True | True | 190.38 | 0.082046466 | 0.000000 |
| 1 | 100 / 160 | True | True | 187.36 | 0.096310220 | 0.142448 |
| 2 | 100 / 120 | True | True | 162.96 | 0.111443019 | 0.293575 |
| 3 | 100 / 100 | True | True | 177.50 | 0.116152611 | 0.340608 |
| 4 | 100 / 140 | True | True | 179.44 | 0.106476476 | 0.243975 |
| 5 | 140 / 100 | True | True | 174.93 | 0.119021792 | 0.369262 |
| 6 | 140 / 140 | False | False | 127.54 | — | — |

**Finding:** The tested generic direct baseline does not attain the stored strong reference within its budget. This is a witnessed outcome for this algorithm, not proof that every generic direct method fails.

Median full 51-point operating-point time: **91.93 s**; median `low_energy` call: **1.530 s**. These API calls include factorization and residual checks. Maximum observed completed-worker peak RSS: **175.8 MiB**. These timings measure forward cost, separately from the attained objective.

## Explicitly unexecuted estimates

- An unpruned 140-geometry parameter grid at the observed median full-evaluation time would cost approximately **6.94 hours**. This grid was **not executed**; feasibility pruning and shape-dependent costs can change the estimate.
- Extending the 60-second dense single-point watchdog to 153 points with ideal two-way parallelism gives a **4590-second proxy**, not a measured complete evaluation or a universal dense lower bound.

## Audit and artifacts

`best_result.json` is identical to the best fully evaluated feasible candidate; partial candidates are excluded. `events.jsonl`, every `candidate_*_scenario_*.json`, `direct_history.json`, `direct_report.json`, and `report.json` preserve timings, exact gaps, topology, affinity, limits, and best-so-far state. `setup_failure/` separately preserves an initial inherited-RLIMIT setup error before any forward calculation; it is excluded from numerical evidence. No running participant files, evaluator, challenge pool, or attempt were changed.
