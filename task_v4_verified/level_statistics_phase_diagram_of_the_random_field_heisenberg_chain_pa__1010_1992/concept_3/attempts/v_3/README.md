# Static spectral-center witness

The submission is `witness.json`: a static twelve-site field profile with
the schema and orientation required by `TASK.md`. No submission code is
executed by the evaluator.

The implementation assets perform exact full-sector diagonalizations using
the supplied read-only `workspace/exact.py`. Search includes unstructured,
staggered, domain-structured, and locally perturbed profiles. Search workers
use one BLAS thread each, with at most eight concurrent workers.

`validate.py` checks the witness schema, all field and full-spectrum
constraints, and every acceptance threshold. It also reproduces the public
offset bank exactly from its seed, verifies its published SHA-256 hash,
cross-checks the base spectrum with the alternate `evd` LAPACK driver, and
checks spectral trace identities. Additional replication banks use fresh
independent 256-bit seeds and the disclosed SHA-256 generator law; their
protocols are saved alongside the reports.

The committed private bank is unavailable and has not been tested. Public
calibration and solver-generated replication reports are not private grading
results. This concerns the task-authored finite-size proxy claim, not a claim
attributed to Pal and Huse or a thermodynamic conclusion.
