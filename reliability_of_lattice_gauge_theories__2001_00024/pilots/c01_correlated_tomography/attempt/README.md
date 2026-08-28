# Correlated double-well tomography

`solver.py` exposes the required `solve(case: dict) -> dict` entry point. It
depends only on Python, NumPy, and SciPy. A JSON command-line interface is also
available:

```sh
python solver.py path/to/case.json
python solver.py < path/to/case.json
```

Each readout uses centered, inverse-variance-weighted linear regression with
the supplied fixed calibration. Offset and amplitude are unconstrained, and
the amplitude uncertainty uses absolute measurement variances, without
residual rescaling.

The occupation calculation is a linear program on the complete supplied
joint-state distribution. A first program minimizes nonnegative common band
inflation. Separate programs then minimize and maximize every target at that
inflation plus the supplied feasibility pad. Returned witnesses attain the
reported endpoints. Missing observations create no constraints; no symmetry
or factorization assumption is imposed.

For numerical conditioning, an observation is represented by
`D = (response - center) / radius`. Because the probabilities sum to one,
its band is exactly `abs(D @ p) <= 1 + inflation`. This keeps the inflation
variable and the feasibility pad dimensionless. HiGHS solves the programs
with primal and dual feasibility tolerances of `1e-10`.

## Local validation

The implementation passed 320 checks: four analytic population cases, 100
weighted-regression comparisons, 60 independently enumerated small-polytope
cases, 151 comparisons with an unscaled LP formulation (including the supplied
example), and five additional scientific-contract and command-line checks.
The largest observed fit, inflation, and endpoint discrepancies were
`1.51e-13`, `2.12e-13`, and `9.81e-13`, respectively. The largest witness-band
residual was `5.29e-15`.

Additional checks cover sharp joint totals, non-factorized occupation bounds,
missing channels, signed amplitude weights, a zero feasibility pad, and the
absolute-sigma covariance convention. The example takes approximately 0.52
seconds including a fresh Python process and library imports in the local
environment. Its inflation is zero and its `gauge_valid` interval is
`[0.8781134695221128, 1.0]`.
