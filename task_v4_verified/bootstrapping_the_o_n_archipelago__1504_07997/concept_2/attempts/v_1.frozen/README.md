# Sparse mixed-OPE completion

The final submission is `answer.json`. It contains certificates for all eight
instances, using seven or nine distinct atoms as permitted by each instance.
No additional assets are required to grade the submission.

The supplied checker accepts every certificate. Its complete report is saved
in `validation.json`: core score 1.0, worst-family score 1.0, and maximum scaled
componentwise residual approximately 2.5621e-15 (required limit: 2e-8).
All shared-coefficient, coefficient-bound, and trace-budget checks pass.

To repeat validation from this directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python \
  ../../participant/workspace/check.py \
  ../../participant/input/instances.json answer.json
```

Recovery used SVD-preconditioned nonnegative diagonal fits, joint nonlinear
rank-one OPE refinement with the shared coefficient fixed, and discrete
support enumeration ranked by positive rank-one matrix consistency. The
Python scripts and logs in this directory are supporting research artifacts;
grading requires only `answer.json`. Coefficients retain full floating-point
serialization precision.
