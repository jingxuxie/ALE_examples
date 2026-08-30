# Private generation-1 portfolio: closed

Two concrete accelerations were tested. No further tuning is planned.
Total measured portfolio cost was 164.507684239 CPU seconds, below the
900-second cap. This private portfolio found no passing same-budget candidate.
Its former unknown-attainability conclusion is superseded: actual fresh v3
subsequently passed all 20 generation-one cases under the unchanged budget,
with maximum 2.77745 CPU seconds and total 15.836076 CPU seconds. The two private
variants and their reports remain unsuccessful historical evidence.

| Private candidate | Acceleration | Accepted | Core | Worst family | Passed |
| --- | --- | ---: | ---: | ---: | --- |
| candidate_1 | Exact phonon-mode factorization of DCT/DST convolution | 16/20 | 0.80 | 0.50 | No |
| candidate_2 | Factorization plus normal-eigenmode/projected-amplitude initialization | 16/20 | 0.80 | 0.50 | No |

Both complete evaluations use the unchanged 12-CPU-second, 2048-MiB,
single-process/single-thread policy. All eight failures are CPU-limit exits on
the four large-grid replacements, not observed branch or output-format errors.
Exact mode factorization avoids the dense patch-pair/frequency tensor but does
not reduce the remaining transform/contraction work enough. Eigenmode seeding
reduces nonlinear startup work but still incurs full-grid eigen/Krylov work.
These observations do not constitute a detailed per-kernel timing profile.

An extended candidate_2 diagnostic on case_16 finishes in 16.126348 CPU seconds,
with gap residual 6.99496e-14, Z residual 7.04160e-14, branch error 4.82528e-10,
and correct relative signs. It validates numerical quality, not the 12-second
joint target. Two sandboxed map/JVP comparisons against the supplied public
operator also pass.

The final read-only integrity check verifies all 92 activated seal hashes.
Participant, evaluator, status, and the v3 trial were not changed. All writes
from this portfolio stay within this private sidecar. Inference reads only the
public instance; it contains no reference arrays, case IDs, or fixture lookup.

Retained runnable artifacts are `candidate_1/solve.py` and `candidate_2/solve.py`.
Complete frozen-evaluator reports are `candidate_1_report.json` and
`candidate_2_report.json`; additional evidence is in `summary.json`,
`extended_diagnostic.json`, `self_check_report.json`, and `portfolio.log`.
Preparation and bounded orchestration code are retained for provenance.

From the active concept directory, a private replay can be run with:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python -B evaluator/evaluate.py --submission adversary/privileged_generation1/candidate_2 --report adversary/privileged_generation1/replay_report.json
```

No replay or further search is being started as part of this closeout.
