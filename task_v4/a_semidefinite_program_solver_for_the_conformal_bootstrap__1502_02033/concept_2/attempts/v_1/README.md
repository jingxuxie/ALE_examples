# Successful continuum-screen counterexample

The submission is `witness.json`, a 1,072-byte JSON object containing a degree-four rational symmetric matrix polynomial. The denominator is exactly `1000000000000`.

## Exact evidence

The submitted point and direction are

```
x = 102757701/200000000
v = (1/5, 2/5, 2/5, 4/5)
```

The direction has squared norm one and is an exact eigenvector at the witness. Its normalized Rayleigh quotient is

```
-20401878022973897611 / 200000000000000000000000000
  = approximately -1.0200939011486948e-7,
```

strictly below the required `-1e-7`. All contract conditions were checked using Python's exact `fractions.Fraction` arithmetic, independently of the floating screen. The smallest diagonal at the witness is approximately `0.041040894116497716`; the smallest two-coordinate principal determinant is approximately `0.00017286570695029173`. The squared Frobenius norm of the required commutator is approximately `0.00015224154767431593`, comfortably above `1e-8`. The maximum coefficient row sum is `1.574120183364`, below four. `exact_validation.json` records the exact fractions as well as approximations.

## Frozen public guard result

Running the unmodified participant guard on the final JSON reports acceptance in all three profiles:

| Profile | Accepted | Minimum seen | Matrix evaluations |
| --- | --- | --- | --- |
| `uniform_lobatto` | yes | `-1.6192559446071009e-16` | 3210 |
| `shifted_lobatto` | yes | `-1.942890293094024e-16` | 3304 |
| `incommensurate` | yes | `-2.0122792321330962e-16` | 3422 |

Each profile reaches the final frozen-Rayleigh stage, with 21 determinant candidates and no bounded local optimizations. The full public CLI output is preserved in `guard_report.json`. No private evaluator was available or used.

## Construction and mechanism

An exact rational orthogonal change of coordinates transforms a block polynomial with four spectral coordinates: a narrow negative quadratic branch, a constant zero branch, and a coupled two-by-two block with a broad, nonnegative, almost-flat quartic minimum away from the negative point. The last diagonal enforces trace one exactly. Integer rounding is performed before the rational orthogonal transformation, preserving the common nullspace and the quadratic direction exactly.

The common null direction is `(-2/5, 1/5, 4/5, -2/5)`. Consequently, the exact determinant is identically zero, so its floating expansion provides roundoff-dependent candidates rather than reliable information about the negative branch. Away from the narrow negative interval, the lowest eigenvalue is zero up to roundoff; this suppresses the guard's sampled-basin optimization trigger. The nearly flat quartic branch attracts the small-gap refinement and second-eigenvector seeds away from the negative interval. The nonzero off-diagonal of the two-by-two block makes matrix values genuinely noncommuting. The contract explicitly allows reducible subblocks; the complete polynomial is not simultaneously diagonalizable.

The rational rotation spreads the witness across every original coordinate. Exact diagonal and two-coordinate minor checks ensure that neither a one-coordinate nor a two-coordinate direction can expose the failure at the submitted point.

## Reproduction

From this output directory:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
python validate_exact.py witness.json --output exact_validation.json
python ../../participant/workspace/guard.py witness.json
```

`search.py --trials 1000 --seed 42` regenerates the successful candidate on its first trial with the supplied NumPy/SciPy environment. It writes `witness.json` and `best_reports.json`. `search_decoy4.log` preserves the successful search, and `search_degree2.log` preserves the earlier unsuccessful quadratic-decoy experiment. The initial quadratic decoy was replaced with a quartic decoy in the final search implementation.

The evaluator needs only `witness.json`; all other files are supporting verification and scratch work. Participant assets were not modified.
