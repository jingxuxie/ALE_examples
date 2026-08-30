# Critical Ising uniform MPS submission

The final artifact is `state.npz`, a regular NumPy archive containing only the
real float64 array `A`, with shape `(2,24,24)` and size 9,472 bytes.

The supplied public checker confirms **valid: true**, **passed: true**,
**core_score: 1.0**, and **worst_family_score: 1.0**. Its complete output is
saved in `final_check.json`; runtime was 5.32 seconds.

| Family | Measured error | Required maximum |
| --- | ---: | ---: |
| Energy excess | 1.2538493082e-5 | 5e-5 |
| Order, maximum relative error | 0.0064794688 | 0.025 |
| Connected density, maximum relative error | 0.0133539468 | 0.1 |
| Y spin, maximum relative error | 0.0127805224 | 0.1 |
| Two-interval covariance, maximum relative error | 0.0064915810 | 0.01 |
| Three-interval K3, maximum relative error | 0.0660537537 | 0.1 |

The canonical defect is 1.46e-15 and the parity defect is zero. The stationary
density has minimum eigenvalue 4.65e-8; the second transfer eigenvalue modulus
is 0.9998331921. All required distances, 60 quartets, and 252 sextuples were
checked using the full submitted tensor and its actual stationary boundaries.

## Construction and checks

`optimize.py` starts from the provided bond-24 baseline and optimizes its real
parity-preserving blocks. Cholesky row normalization enforces right
canonicality throughout optimization. Reduced symmetric and antisymmetric
transfer sectors give differentiable, finite-dimensional contractions, with
the stationary density obtained from a constrained linear solve. Pair
operators are centered with their own submitted-state means before computing
connected composite moments. This is algebraically the literal cumulant
subtraction, not a Gaussian assumption or a replacement by exact means.

SciPy L-BFGS-B first minimizes normalized squared observable errors, then a
hinge objective improves the worst errors while preserving margins in the
other families. All computations use installed CPU NumPy, SciPy, and PyTorch.
Contractions were compared against the public checker on the baseline, with
absolute discrepancies below 5e-14; a directional finite-difference check
also confirms the objective gradient. These checks are recorded in
`implementation_check.log`. The final artifact is independently checked by
the unmodified participant checker in `final_check.json`.

SHA-256 of `state.npz`:
`f2d3791e6224c285e5d4f9cf8d0170cc28c75745215ffb622654fd0fa646bb03`.
