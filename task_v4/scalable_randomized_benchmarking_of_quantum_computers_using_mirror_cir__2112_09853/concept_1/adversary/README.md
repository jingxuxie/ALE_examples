# Private B search and independent verification

Keep this directory out of participant-visible files. Nothing here imports or modifies the public workspace, model, or evaluator.

## Contents

- `winning_witness.json`: the integer witness reported in the design handoff, not a rounded relaxation.
- `search.py`: reproducible private search from an explicitly constructed feasible non-winning initialization; it does not load the winning witness.
- `verify.py`: independent tuple-based Pauli implementation, exact integer constraint checks, a dense mirror transfer, and a separate short-depth probability-convolution check.
- Run evidence files document actual subprocess executions, versions, commands, timings, source hashes, and results. They are generated with `apply_patch` from captured subprocess output.

## Reproduce

Run inside this directory, with Python, NumPy, and SciPy available:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python search.py --verify-gradient
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify.py winning_witness.json --require-winning
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify.py --baseline
```

Programs emit JSON to stdout and do not create files. A successful baseline verification reports `admissible: true` but `accepted: false`, because the baseline misses the bias target. `--require-winning` turns an acceptance failure into a nonzero exit status.

## Exact conventions

Local digits are `0=I, 1=X, 2=Z, 3=Y`. Single-qubit classes are lexicographic permutations of `(1,2,3)` giving images of `(X,Z,Y)`. Single error columns are `(X,Z,Y)`. CNOT rows are `(0,1),(0,3),(1,2),(1,0),(2,3),(2,1),(3,0),(3,2)`. For CNOT column `k-1`, `k=1..15`, the control and target digits are `k%4` and `k//4`.

Each single class has weight `1/40`; each CNOT class has weight `2/40`. Noise is after the ideal gate, with identity probability `0.98` and nonidentity probabilities `count/3000`. Every row sums to 60. Bounds are `[2,42]` for single-qubit rows and `[1,21]` for CNOT rows.

The verifier recomputes all 255 nonidentity weighted marginal constraints using Python integers. Twelve weight-one marginals equal 152; 36 ring-edge weight-two marginals equal 16; all other 207 equal zero. It independently computes the 32 weighted inverse-pair overlap terms, whose exact sum must be 32640. It also compares the resulting exact rational depth-two polarization with the floating-point transfer result.

The independent verifier uses four-digit Pauli tuples, whereas search uses bit masks `x+16*z`. The verifier does not import search. Its probability-space convolution cross-check tests mirror depths 2, 4, 6, and 8 without using the Pauli eigenvalue recurrence.

## Search algorithm

There are 192 counts, 79 independent linear equalities, and one quadratic overlap equality. Search works on conditional probabilities `count/60`. A rank-revealing QR selects independent linear constraints. Initialization adds `[18,-18,0]` to each qubit's identity-class row and subtracts it from that qubit's `(2,1,3)` class; this preserves both the average channel and the overlap exactly while avoiding the uniform point's degenerate overlap gradient.

SLSQP optimizes the fitted rate with an adjoint through the 128 transfer steps and an implicit derivative of the two-parameter exponential fit. A deterministic finite-difference directional check validates the gradient. The continuous objective penalizes residuals above 0.008 to stabilize search; final acceptance always uses the stricter 0.004 condition. Search's fit uses bounded scalar optimization; the independent verifier uses the specified 4,097-point scan and refines all grid-local minima, including interval endpoints in the final comparison.

The continuous solution is rounded. Search verifies that all linear equalities survive rounding, then enumerates bounded four-cell integer transportation moves between gate classes with identical supports. It checks every one-move and two-move repair of the exact quadratic overlap, evaluates repaired curves, and returns the best rate meeting the final residual and signal constraints. Differences in numerical libraries can change the continuous optimum or symmetry-related repair selected. A failed rounding/repair is reported explicitly rather than silently relaxing constraints.

## Acceptance and scientific scope

The depth grid is `0,2,...,256`. Fit `A*exp(-t*d)` without an additive offset, with `t` in `[0.005,0.04]`, minimizing unweighted squared polarization residuals. Define `r=(255/256)*(1-exp(-t))` and `bias=1-r/0.02`. Require all integer constraints, maximum residual at most `0.004`, depth-256 polarization at least `0.005`, and bias at least `0.0244`.

The original handoff's approximate witness values were `r=0.019510123175640538`, `bias=0.024493841217973156`, maximum residual `0.0039005466452401993`, and `S256=0.006549008866188657`. The saved independent run evidence is authoritative for the prescribed grid/refinement fitting procedure; last digits can differ from the original bounded-only fit.

This tests a deliberately strengthened quantitative robustness claim seeded by arXiv:2112.09853, not a theorem stated by that paper. Every layer has the same 2% infidelity; the mean Pauli channel and the depth-two mirror signal match the baseline. The discrepancy concerns higher-depth noise/gate correlations. No fresh-agent one-hour difficulty test has been performed, and rapid privileged search is not evidence of participant difficulty.
