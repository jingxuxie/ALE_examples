# Falsify a frozen NLO EEC quadrature error estimate

## Mission: quadrature, not inaccurate function evaluation

Submit a **static `witness.json`** specifying one smooth, signed angular-moment
weight. It must make the supplied deterministic integrator report convergence
with materially underestimated integration error for **all three QCD color
contributions**, using the same weight and finite angular bin.

This is an inverse numerical-design task, not an integrator implementation
contest. The integrator, kernel, tolerances, admissible domain and grading
conditions are fixed. Do not replace, monkey-patch, or submit an integrator.
Only the JSON is read. Nothing in your submission directory is imported.

We distinguish three errors:

1. **Quadrature error**: the frozen adaptive answer differs from a converged
   integral of the same frozen integrand. This is the requested counterexample.
2. **Integrand evaluation error**: the frozen EEC kernel differs from the
   high-precision analytic source. Material disagreement disqualifies the
   quadrature claim; this is NOT an end-to-end uncertainty mission.
3. **Point-versus-bin mismatch**: comparing a midpoint value with a finite-bin
   integral is not allowed. All target and reference computations integrate
   precisely the same bin, Jacobian, response and signed weight.

## Physical observable

The source is Dixon et al., arXiv:1801.03219v2, Eqs. (7)--(10) and the
supplemental color components. Let `z=(1-cos(chi))/2`, `t=(z-a)/(b-a)`.
With `Nc=3`, `Nf=5`, at renormalization scale `mu=Q`, the NLO coefficient is

```
B(z) = (16/9) B_lc(z) + (4/9) B_nlc(z) + (10/3) B_Nf(z).
```

The three independently checked moments are

```
I_c = 2 integral_a^b dz [4 z(1-z)] color_c B_c(z) R(t) W(t).
```

The factor 2 is the absolute `d cos(chi)/dz` Jacobian; `4z(1-z)=sin^2(chi)`.
We work in units of the NLO coefficient, omitting the common coupling factor
`(alpha_s/(2*pi))^2`. These color-resolved signed moments are linear diagnostic
observables, not positive probability distributions or resummed predictions.

Exactly three bins are available:

| `bin` | `a` | `b` |
|---|---:|---:|
| `collinear` | 0.02 | 0.32 |
| `central` | 0.08 | 0.92 |
| `backward` | 0.60 | 0.98 |

There are no endpoint distributions in these finite, strictly interior bins.
Neither endpoint can be approached arbitrarily closely.

## Finite parameter domain

For integer `band_start` in `[1,53]`, define twelve consecutive frequencies
`k=band_start,...,band_start+11`, hence no frequency exceeds 64:

```
W(t) = sum_j [cosine[j] cos(2*pi*k_j*t) + sine[j] sin(2*pi*k_j*t)] / 10^10
s = 2*t - 1
R(t) = [1 + (tilt/16)*s + (curvature/16)*(s*s - 1/3)] / 1.5.
```

`tilt` and `curvature` are integers in `[-4,4]`. The detector response is
positive and broad: `7/18 <= R <= 17/18`. `W` is a bounded Fourier analysis
weight, which may change sign; it is not a detector efficiency. Both arrays
contain exactly twelve integers, and their combined integer coefficients `q`
must satisfy

```
sum(abs(q)) <= 10^10
sum(q*q) >= 10^20 / 50.
```

Consequently `|W|<=1` and its full-bin Fourier RMS is at least 0.1. The fixed
band limit bounds derivatives and excludes arbitrarily narrow features. You
cannot submit arbitrary functions, node-factor polynomials, discontinuities,
new response shapes, or free color parameters. All parameters live on a finite
lattice; coefficient decimal strings or floating JSON values are invalid.

Schema (this simple example is valid but is not promised to falsify anything):

```json
{
  "version": 1,
  "bin": "central",
  "band_start": 1,
  "tilt": 0,
  "curvature": 0,
  "cosine": [10000000000,0,0,0,0,0,0,0,0,0,0,0],
  "sine": [0,0,0,0,0,0,0,0,0,0,0,0]
}
```

No additional fields, booleans, duplicate keys, nonfinite values or symlinks
are accepted. The file is limited to 16 KiB.

## Supplied strong target

`input/target.py` implements real binary64 Gauss(10)-Kronrod(21) quadrature.
The Gauss nodes are nested within the Kronrod nodes. It includes four coarse
pilot panels and compulsory refinement to eight, absolute-deviation error
rescaling as in QUADPACK's `dqk21`, a `50*eps*L1` roundoff floor, additional
parent/children discrepancy checks, summed nonnegative local estimates, and
largest-error adaptive bisection up to 512 panels. It never substitutes a
fabricated answer, hardcoded estimate, or participant-supplied value.

The claimed tolerance is `tau=max(2e-8, 2e-9*abs(answer))`. Reaching the panel
cap without satisfying the estimate is a failure, not a counterexample.
The supplied kernel is a stable, source-calibrated piecewise Chebyshev
representation; it avoids evaluating the cancellation-prone raw formula in
binary64. Its high-precision calibration is checked at increasing degree and
precision, separately from quadrature validation.

## Fixed success and scoring

For each color family, the evaluator independently computes two references
using degree/precision `(64,50 dps)` and `(88,80 dps)`, composite Gauss-Legendre
orders 24/36 and 32/64 subdivisions, split additionally at expansion boundaries.
Two further refined binary64 integrals of the actual frozen integrand use
orders 40/56 and 64/128 subdivisions. Neither an approximate expansion nor a
single numerical rule is declared exact.

The high-precision signed references must agree within `1e-18*max(1,|I|)`.
Both frozen-grid agreement and frozen/source agreement must be at most `2e-10`.
Let `u=max(2e-11,100*high_precision_gap,10*frozen_gap,10*source_frozen_gap)`.
Let `E` be the smaller of the source and frozen true-error estimates, minus
`u`, clipped below at zero. To avoid a materiality decision based on an
optimistic absolute-value integral, use
`L=max(L_coarse,L_fine)+4*abs(L_coarse-L_fine)` for the reference L1 scale.

Each family must satisfy

```
target.converged == true
E >= max(20*tau, 50*target.estimated_error, 1e-5*L).
```

An unresolved reference receives zero family score. Otherwise a converged
family scores `min(1, E/required_error)`; nonconvergence scores zero.
`core_score` is the mean of the three scores; `worst_family_score` is their
minimum. `passed` requires all three conditions. `valid` only means the static
witness and trusted assets are admissible, not that it is a counterexample.
Runtime/resource scores are 1 for admissible static witnesses, 0 for invalid
ones; wall-clock grading time is reported separately and not optimized.

These are stringent numerical convergence checks with conservative allowances,
not a claim of a theorem-level interval enclosure for the analytic EEC.

## Local workflow

From this participant directory:

```bash
OPENBLAS_NUM_THREADS=1 python baseline/search.py workspace --trials 24
OPENBLAS_NUM_THREADS=1 python input/local_api.py workspace --trace --report workspace/local_report.json
```

Your Python can import `problem.Kernel`, `problem.validate`, `target.integrate`,
and `local_api.measure` after adding `input` to its module search path. The API
provides diagnostics and a refined **screening** estimate, not private grading
references. A successful local screen is not certification.

NumPy, SciPy and mpmath are available; no network is needed. The official
author-side interface is `python evaluator/evaluate.py SUBMISSION_DIR --report
PATH`. Deliver only the directory containing your static `witness.json`.
