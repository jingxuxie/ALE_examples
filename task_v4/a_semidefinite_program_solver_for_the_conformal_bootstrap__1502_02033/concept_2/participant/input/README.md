# Witness contract, version 1

One UTF-8 JSON object, at most 65,536 bytes, with exactly these keys:

```json
{
  "schema_version": 1,
  "denominator": 1000000000,
  "coefficients": ["replace with degree+1 integer 4-by-4 matrices"],
  "x": "2/5",
  "vector": ["1/5", "2/5", "2/5", "4/5"]
}
```

This schematic is not a submission. `example_rejected.json` is a complete file.

## Exact polynomial

Let `Q = denominator`, `A[k] = coefficients[k]`, and

`M(x) = sum(k=0..d) (A[k]/Q) T_k(2x-1)`.

Here `T_0(t)=1`, `T_1(t)=t`, `T_(k+1)(t)=2t T_k(t)-T_(k-1)(t)`.
Every entry of `A[k]` is a JSON integer, **not** a floating number or a rational
string. Rational strings are used only for `x` and the four vector components.

- `Q` is an integer in `[1,10^12]`. Degree `d` lies in `[2,24]` and `A[d]` is
  nonzero. All matrices have exactly four rows and four columns.
- Every `A[k]` is exactly symmetric and every numerator has absolute value at
  most `Q`. `trace(A[0])=Q`; all other traces vanish exactly.
- For each row `i`, `sum(k,j) abs(A[k][i][j]) <= 4Q`. Consequently the symmetric
  matrix has spectral norm at most four throughout the interval. These are
  scale/representation bounds, **not** a lower bound on small eigenvalues or
  root separation: near-singular matrices and clustered roots are intentional.
- The squared Frobenius norm of
  `[M(1/4), M(3/4)] = M(1/4)M(3/4)-M(3/4)M(1/4)` is at least `10^-8`.
  Thus the whole polynomial cannot be diagonalized in a constant orthogonal
  basis. This condition does not claim irreducibility of every subblock.

## Rational evidence

Use canonical reduced strings such as `"0"`, `"-3/7"`, `"2/5"`. No decimal,
scientific, `+`, whitespace, negative-denominator, or unreduced forms are allowed.
Numerators have absolute value at most `10^12`; denominators are positive and at
most `10^12`. JSON duplicate/unknown keys, booleans in integer fields, floats,
NaN, infinities, and oversized or ragged arrays are rejected.

- `1/20 <= x <= 19/20`.
- Each vector component has absolute value at most one.
- `1/4 <= v^T v <= 4`; every `v_i^2 >= (v^T v)/100`.
- At the submitted point, every diagonal of `M(x)` is at least `1/50`, and all
  six principal `2x2` determinants are at least `10^-5`. Thus no direction
  supported on only one or two coordinates witnesses the failure.
- Successful evidence must satisfy **`v^T M(x) v / (v^T v) <= -1/10^7` exactly**.
  The evaluator uses fractions, not a high-precision approximation or the
  participant's reported eigenvalue. It does not tell the guard `x` or `v`.

## Fixed screen and scoring

The public source is the target specification. Each of three deterministic
profiles combines an endpoint/uniform mesh, a cosine mesh, and incommensurate
nodes. The screen also constructs every principal minor in the Chebyshev basis,
examines companion roots of each and its derivative, including real projections
of **all** complex roots whose real parts are in the interval, refines 24 risky
intervals for three rounds, minimizes sampled eigenvalue basins (up to 64), and
searches stationary points of frozen Rayleigh polynomials. Near-degenerate
seeds include the second eigenvector. No monomial conversion, sampled
determinant interpolation, or real-root imaginary-part cutoff is used.

Any eigenvalue below `-5e-11` causes rejection. Numerical exceptions and failed
optimizations are rejections, never acceptances. These are floating heuristics,
not exact root isolation, interval bounds, or SOS/SDP verification. The public
CLI previews screening only, not exact admissibility. All three profile
parameters and budgets are public and fixed; there is no hidden random seed.

- `valid`: all schema, scale, symmetry, trace, coupling, point/vector, and
  principal-minor constraints hold. It does **not** assert negative evidence.
- `evidence_valid`: the exact normalized quotient reaches the negativity bound.
- `core_score`: fraction of profiles accepting, gated on both flags above.
- `worst_family_score`: minimum of the three gated acceptance indicators.
- `passed`: both flags hold and **all three** profiles accept.
- `runtime_score`: zero unless passed, then `min(1,3/cpu_seconds)`; CPU seconds
  cover evaluation including private module loading, not participant search.
- `reason`: explains rejection, insufficient evidence, or full success.

The private evaluator and its hash manifest are outside the writable
participant deployment. Changing local `guard.py` cannot change the target.

## Relation to a half-line

For `s>=0`, let `P(s)=(1+s)^d M(s/(1+s))`. This is a rational-coefficient
polynomial matrix; its prefactor is positive. An interior counterexample maps
to finite `s=x/(1-x)`. Continuity supplies the limiting endpoint in the reverse
PSD implication. Trace normalization is imposed on `M`, not its homogenization.
