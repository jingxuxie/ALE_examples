# Critical Ising vacuum tensor

The submission is the regular NumPy archive `state.npz`, containing only the
real, double-precision tensor `A` with shape `(2,24,24)`.

Construction starts from the supplied baseline. `optimize.py` fits the exact
energy, order, connected-density, y-spin, and all 60 composite-order covariance
targets. The composite contractions subtract the fitted state's own interval
means. Symmetry is exact by block construction; blockwise Cholesky
orthonormalization enforces right canonical form. A linear solve computes the
thermodynamic stationary density, while binary transfer powers evaluate the
correlations. Autodifferentiation and L-BFGS optimize the tensor parameters.

The reduced-space contractions were checked against the public full-space
checker, and gradients were checked with centered finite differences. The
optimization samples the two-point distances; final validation checks every
required distance and quartet, as well as admissibility and primitivity.

`validation.json` contains the complete final public-checker results;
`summary.json` contains compact metrics. `check_model.log` records the
contraction and gradient checks. The optimization logs and intermediate
candidate archives are retained for reproducibility.

From this directory, with the supplied participant workspace on `PYTHONPATH`:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH=../../participant/workspace
python optimize.py --initial ../../participant/baseline/state.npz --check
python optimize.py --initial ../../participant/baseline/state.npz --prefix first --iterations 2000 --seconds 1000
python finalize.py first_best.npz first_last.npz candidate_check.npz
python ../../participant/workspace/check.py state.npz
```
