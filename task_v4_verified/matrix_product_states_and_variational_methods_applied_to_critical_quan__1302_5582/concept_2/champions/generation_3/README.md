# Critical Ising uniform MPS submission

The submission artifact is `state.npz`, a regular 9,472-byte NumPy archive
containing only the real float64 array `A`, with shape `(2, 24, 24)`.

The supplied public checker reports **valid: true**, **passed: true**, and
both core and worst-family scores of **1.0**. Full public-checker results are
in `final_check.json`; `validation.json` also contains an independent
parity-sector contraction check and the artifact SHA-256.

## Final errors

| Witness | Maximum error | Contract limit |
| --- | ---: | ---: |
| Energy excess | 0.00000583055301 | 0.00005 |
| Order, relative | 0.00417293574 | 0.025 |
| Connected density, relative | 0.00369288462 | 0.1 |
| Y spin, relative | 0.00586205958 | 0.1 |
| Composite order covariance, relative | 0.00375601721 | 0.01 |

All 1,024 order distances, 256 density distances, 128 y-spin distances, and
60 composite geometries were checked. The composite error is approximately
0.376 percent, below the one-percent requirement.

The canonical defect is 1.86e-15, the parity defect is exactly zero, and the
stationary-density residual is 1.41e-15. The minimum density eigenvalue is
3.59e-8; the largest nontrivial transfer eigenvalue modulus is 0.9998243050.

## Construction

`optimize.py` starts exclusively from the provided baseline tensor. Two real
row-isometries, parameterized with QR decompositions, enforce right
canonicality and the specified parity blocks. Symmetric and antisymmetric
transfer sectors reduce the numerical contractions. The infinite-chain
stationary density is obtained by a normalized linear solve, not a finite
chain approximation. Transfer matrix powers evaluate the multiscale
observables and centered interval environments evaluate the composite
covariance using the submitted state's own interval means.

Double-precision automatic differentiation and CPU L-BFGS-B minimize a joint
energy and relative-observable-error objective. Optimization samples the
two-point distances and uses every composite geometry; final validation
covers every specified distance. Directional finite differences check the
automatic gradient (`implementation_check.log`). The selected checkpoint
is `run1_loss.npz`; `run1.log` records the optimization trajectory. The
optimizer was stopped after obtaining a comfortably passing tensor.

## Verification

From the participant directory, run:

```sh
python workspace/check.py ../attempts/v_6/state.npz
```

From this output directory, the additional independent check is:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 python validate.py state.npz
```

The independent full-distance sector calculation agrees with the public
checker to within 4e-9 in maximum relative-error statistics.
