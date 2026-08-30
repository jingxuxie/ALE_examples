# Exhaustively verified candidate

`witness.json` is the strongest candidate found during this attempt. It is
structurally valid, but **it does not pass all seven scientific gates**. No
passing witness was found; this submission is not a claim that the mission's
complete counterexample has been constructed.

The final metrics and failed gates are recorded in `verification.json` and
independently recomputed in `independent_verification.json`.

## Reproduce verification

Run from this directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B verify.py witness.json
```

The verifier explicitly enumerates all 65,536 physical spin configurations in
float64. It evaluates the target partition function, proposal probabilities,
centered reward variance, all 120 ambient gradient coordinates, entropy, reverse
KL, dimensionless energy error, and both antipodal-sector masses. It does not
clip, discard, floor, or renormalize proposal probabilities.

The row L1 bound implies every conditional outcome has probability at least
0.01. Zero biases imply exact global spin-flip symmetry algebraically; the
exhaustive verifier also checks normalization and numerical symmetry.

## Construction and numerical checks

The search explores frustrated bond assignments, spin orders, directed-tree
initializations selected by subset dynamic programming, and constrained
continuous weight optimization. The final refinement minimizes an epigraph of
the simultaneous gate ratios, using exact gradients and the exact KL Hessian.

`fast.cpp` supplies the accelerated half-space search calculations, while
`verify.py` implements the independent full-space check. `final_numerics.log`
records agreement between these implementations and finite-difference checks
of the search derivatives. Earlier tests also compare Hessian-vector products
against finite differences and the independently assembled full Hessian.

The remaining Python files and candidate JSON files preserve the search work;
only `witness.json` is the evaluation submission.
