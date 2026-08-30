# Private numerical reference and provenance

The participant receives only a derived stable binary64 kernel, not the paper,
the original source formula, prior submissions, private calibration tables,
construction search, or accepted witnesses. All such material here is private.

`native_kernel.py` copies the three internal component functions and their
basis helpers from the explicitly authorized prior `solution/v_01/solve.py`.
The old public wrapper was omitted: it fixed precision and returned a float.
The retained functions instead run entirely in the caller's mpmath context.
No monkey-patching of mpmath or reduced-precision source evaluation is used.

Source identification: Dixon, Luo, Shtabovenko, Yang and Zhu,
*The Energy-Energy Correlation at Next-to-Leading Order in QCD, Analytically*,
arXiv:1801.03219v2, 11 January 2018. The source uses Eq. (9), the basis in
Eq. (10), and supplemental Eqs. (13a), (14a), (15a). The author checked the
coefficient arrays, signs, denominators and the two additional weight-three
functions against arXiv's rendered supplemental equations on 28 August 2026.
The separately commissioned official ancillary-source audit remains a distinct
main-orchestrator check; this document does not claim that audit was performed
by this builder.

`build_kernel.py` generates all three colors jointly on nine fixed interior
z intervals. The quantity tabulated is `4*z*(1-z)*B_c(z)`. It performs DCT
interpolation at Gauss-Chebyshev nodes with degree/working-precision levels
40/60, 64/85 and 88/110. The public float table is the degree-64 level.
The calibration audit reports 153 independent off-node source checks at each
level, tail norms, and coefficient-l1 bounds on the uniform difference between
successive polynomials. These last bounds are genuine polynomial bounds;
they are NOT asserted to bound the error against the unknown exact function.

Measured uniform polynomial differences are approximately 5.84e-21 and
1.70e-33. Off-node source residuals are approximately 3.04e-21, 1.20e-33 and
3.95e-46. Their scale and improvement support numerical convergence. A
generous absolute 2e-11 floor is subtracted from every claimed quadrature error.

`reference.py` independently integrates each candidate using high-precision
composite Gauss-Legendre rules at two degree/precision/refinement levels. It
also integrates the actual frozen binary64 function at two higher-resolution
grids. It fails closed on reference disagreement or material frozen/source
disagreement. Its allowance includes all measured discrepancies with safety
factors. The absolute-value moment only enters a conservative materiality
scale, not the signed reference.

`adversary/verify_native.py` is an additional, expensive champion audit: it
integrates the original polylogarithmic formulas directly at 50 and 80 dps,
without any surrogate, and compares both native values with the independently
refined surrogate result. This is not run on every submitted JSON. Reference
tables are never called exact, and these checks are not an interval-arithmetic
proof of the analytic integral.

`frozen_manifest.json` locks the actual target, finite domain, public kernel,
and private reference assets. The target/domain/public-kernel hashes also match
`adversary/presearch_hashes.json`, taken before any privileged witness search.
No target or domain was weakened after a failed search.

Reproduce from the concept root with `PYTHONDONTWRITEBYTECODE=1` and
`OPENBLAS_NUM_THREADS=1`:

```
python evaluator/hidden/test_numerics.py
python participant/baseline/search.py attempts/baseline --trials 24
python evaluator/evaluate.py attempts/baseline --report attempts/baseline/report.json
python adversary/search.py --max-configs 99
python adversary/search_localized.py
python adversary/search_single_leaf.py
python adversary/verify_native.py
```

Rebuilding the source tables is optional and takes around a minute on the
author machine. It should reproduce the public kernel hash exactly; the audit
wall time is naturally different. Do not regenerate the release manifest
silently after modifying a graded asset.
