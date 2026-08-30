# Certified CCSD population counterexample

`submission.json` is the final artifact, in the unchanged four-field schema required by the task. It contains the symmetric 15-by-15 pair matrix and 18 stationary CCSD amplitudes.

## Verification

The public oracle passes all 241 stencil endpoints and all 241 original continuation certificates, covering 15,665 continuation nodes. The certified core score is **0.02300003355999538**, giving the task's normalized score of **1**.

| Worst stencil diagnostic | Observed | Required |
| --- | ---: | ---: |
| Population violation | 0.02300003356 | >= 0.02 |
| Absolute ground energy error | 0.00009500322 | <= 0.0001 |
| Density asymmetry diagnostic | 0.00095139060 | <= 0.001 |
| Ground-state squared overlap | 0.99999852766 | >= 0.999 |
| Reference weight | 0.69021040448 | >= 0.45 |
| Exact excitation gap | 0.14086721266 | >= 0.1 |
| Real HF curvature | 0.32164535387 | >= 0.05 |
| Imaginary HF curvature | 0.51997004018 | >= 0.05 |
| Jacobian condition number | 48.065490334 | <= 100 |
| Minimum EOM real part | 0.14815531922 | >= 0.05 |

`verification_summary.json` records the final artifact hash, certified score, coverage, and independent diagnostic extrema. `certify20.full.json` records the public oracle's per-point certificates.

`independent_check.py` separately constructs the full 64-dimensional Fock-space fermion operators, projects the three-particle sector, and uses SciPy matrix exponentials rather than the public oracle's nilpotent-polynomial implementation. It independently checks every stencil endpoint; its results are in `independent20.json`.

## Reproduce

From this output directory:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$(realpath ../../participant/workspace)"
python validate.py submission.json verification
python independent_check.py submission.json independent.json
```

The search scripts and intermediate files are retained as experiments. Only `submission.json` is the submitted witness; no submitted code is needed by the evaluator.
