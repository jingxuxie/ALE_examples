# Private headroom audit: frozen concept 1

This directory is the entire write scope of the sidecar. No fresh Codex session
was launched, no running fresh attempt was inspected, and no frozen package file
was changed. The original 12% overall / 8% per-family targets remain untouched.

## Result

All eight hidden LP relaxations solved. Upper bounds on attainable mean relative
gain are 8.787915% for gap hotspots, 7.926573% for inversion proximity,
5.989040% for anisotropic warping, and 6.520281% for scenario competition.
The family-balanced upper bound is 7.305952%, below the required 12%.
The anisotropic family alone is bounded below its required 8% gain.
No passing implementation is claimed; the new LP-guided search prototype in
`submission/` was not replayed as a purported passing solution.

These bounds are independent of the 90-second execution cap. More search time
cannot resolve the discrepancy within the modeled acceptance problem. Treat a
fresh failure cautiously: these results implicate the fixed target rather than
frontier capability. Leave the active run and frozen package untouched and seek
an independent validity review before changing or interpreting the task.

## Relaxation

Use one candidate marginal at each vertex, one candidate-pair marginal on each
directed positive torus edge, and one four-candidate marginal per plaquette.
Normalize vertex marginals and require exact edge-to-vertex and face-to-edge
consistency. Any integer atlas embeds as indicator marginals.

The acquisition budget is linear in vertex marginals. Keep each scenario's
Chern sum within its declared tolerance, using the cached oriented plaquette
flux. Set prohibited edge/face marginals to zero according to overlap and branch
admissibility. Anchors fix vertex marginals. All scenarios share these marginals.
An epigraph variable bounds every normalized scenario loss; its coefficient and
the weighted-mean loss coefficients reproduce the exact robust objective.

Every candidate in a passing submission has objective <= its frozen baseline.
Because the loss components are nonnegative, its epigraph variable can be chosen
<= that baseline objective. All other marginals lie in [0,1]. Thus the finite
box used in the dual certificate does not exclude an eligible passing atlas.

For `min c*x` with `A*x <= b`, `E*x = d`, and `0 <= x <= u`, any `y <= 0` and
unrestricted `z` give the lower bound

```text
y*b + z*d + sum_j min(0, c_j - (A.T*y + E.T*z)_j) * u_j.
```

This box-residual correction handles imperfect dual feasibility. Coefficients
and solver duals are IEEE binary floats, so their exact rational values can be
accumulated with dyadic integers. Certificates store the sparse matrices and
duals; `certificate.py` computes exact rational bounds. Convert downward and
subtract another 1e-9 from each objective bound for scorer accumulation effects.
This is an exact certificate for the floating-coefficient LP, not a formal
interval proof of every operation in the nonlinear input preprocessing.

## Checks and reproduction

The complete 64-assignment small-torus enumeration checks the LP bound against
the discrete optimum. All eight baseline indicators embed correctly. Verification
reconstructs every LP from frozen inputs, repeats every exact certificate, checks
128 additional arbitrary atlas embeddings, and independently repeats both
anisotropic-family certificates using Python `Fraction` rather than the dyadic
accumulator. It also verifies every frozen file hash.

From the concept directory, in the trusted escalated shell:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout --kill-after=5s 245s python3 -B adversary/headroom/bound_study.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 timeout --kill-after=5s 120s python3 -B adversary/headroom/verify.py
```

Read `status.json`, `bounds.json`, and `verification.json` for measured runtimes,
exact per-case bounds and limitations. No frozen status or evaluator report is
overwritten by these commands.
