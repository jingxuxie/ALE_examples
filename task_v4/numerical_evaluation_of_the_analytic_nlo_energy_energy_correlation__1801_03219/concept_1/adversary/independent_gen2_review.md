# Independent generation-2 review

Date: August 28, 2026. Scope: current `evaluator/evaluate.py`,
`participant/workspace/model.py`, `participant/workspace/polynomial.py`, and
read-only checks against the frozen generation-2 reference/cases. No participant,
evaluator, target, or attempt files were changed. All experiments used in-memory
objects; this report is the only written artifact. No solver agents were launched.

## Confirmed correctness flaw: unresolved intervals erase physical bin mass

**Severity: medium; bin-score soundness for admissible adversarial models.**
The loader accepts any strictly increasing finite binary64 knots, without a
minimum interval width. Both bin integrators map Gauss nodes into global `t`
coordinates and then map those rounded coordinates back into the interval's
Chebyshev coordinate. For a one-ULP-wide interval, every quadrature coordinate
rounds to an endpoint. A polynomial that vanishes with its derivative at both
endpoints can therefore have a nonzero exact integral that both routines report
as zero. The 40-node rule's nominal polynomial exactness does not survive this
coordinate round trip.

Affected paths: the strict-increase-only check in `polynomial.load_model`,
`polynomial.bin_average`, and `model.bin_average` (global-coordinate construction
and the call to `evaluate(..., observable="density")`). `evaluate.py` uses that
last routine directly for the scored finite-bin averages.

### Reproduction, entirely in memory

Use default density charts and this legal **17-scalar, 201-byte** model:

```json
{"knots": [-24.0, 1.0, 1.0000000000000002, 24.0], "coefficients": [[[0.0], [0.0], [0.0]], [[1688849860263936.0, 0.0, -2251799813685248.0, 0.0, 562949953421312.0], [0.0], [0.0]], [[0.0], [0.0], [0.0]]]}
```

On the middle interval, its first-channel density is
`amplitude * (1 - local_coordinate**2)**2`, where
`width = 2**-52` and `amplitude = 1/width`. Elsewhere its density is zero.
Its exact total first-channel density integral is `8/15`.

| Physical averaging bin | Exact first-channel average | Both implemented integrators |
|---|---:|---:|
| `[0, 2]` | `4/15 = 0.2666666666666667` | `0` |
| `[-24, 24]` | `1/90 = 0.0111111111111111` | `0` |
| `[1, nextafter(1,+inf)]` | `2401919801264264.5` | `0` |

The deployment loader accepted it under the 268-scalar cap. To avoid creating
a submission file, the experiment substituted the JSON text for the loader's
read of an existing regular baseline file; the example itself is below the
file-size cap and meets all structural checks. It then exercised the real
unmodified model/bin functions.

The full grader, including its optional 60,001-point broad grid, produces exactly
the same score fields for this model as for a model with identical knots and
coefficient-list lengths but all coefficients zero. Only elapsed time differs.
Both are structurally valid and both fail the actual target: **this is not a
demonstrated passing exploit or evidence that a fresh agent's score is wrong**.
It is a concrete legal-model integration counterexample; increasing point-grid
density alone cannot resolve an interval with no representable interior `t`.

For a subsequent disclosed repair, integrate density-chart polynomials directly
in interval-local coordinates, preferably using their exact Chebyshev
antiderivatives. For residual charts, evaluate the latent polynomial at local
quadrature nodes without the global-coordinate round trip, then reconstruct the
density. Alternatively reject intervals too narrow for the implemented numerical
semantics, with an explicit documented bound. Retain this example as a regression
test. No repair was applied while the fresh attempts are running.

## Other focused checks: no additional concrete flaw found

- The hidden oracle carries explicit charts: ten collinear panels, four density
  panels, and ten backward panels. The evaluator does not accidentally treat
  endpoint residual coefficients as density coefficients. Its 24 reference
  intervals are not subject to the participant's deployment budget, appropriately.
- All 1,606 stored value and derivative samples exactly match evaluation of the
  loaded oracle. Recomputed physical bin averages across all 360 hidden bins
  differ by at most `3.0463e-7` of one tolerance unit. This is a reference-usage
  consistency check, not a replacement for the already supplied native audit.
- At `-4`, the selected observable is central density; at `+4`, it is backward
  residual, as the generation-2 contract specifies. Exact boundaries and their
  immediately preceding floats occur in the hidden samples. Independent density
  reconstruction agrees there to about `4e-14` absolute.
- Bins average the reconstructed physical density **over t**, not the piecewise
  residual observable. Knot splitting is present; no missing chart-boundary
  split was found for valid residual-chart intervals. The confirmed failure is
  loss of local-coordinate resolution, not an H/F or z/t measure substitution.
- The outer loader enforces 268 scalars despite the underlying polynomial
  helper's older standalone 320 default. Nonfinite computed responses are
  rejected. Submitted JSON is parsed, not executed. No concrete code-execution
  exploit was established under a correctly isolated, trusted participant bundle.

This review treats generation 2 as the explicitly new endpoint-residual ratchet.
It makes no claim that generation 1 violated its different contract. Ordinary
well-separated fresh submissions are not invalidated by this adversarial example.
