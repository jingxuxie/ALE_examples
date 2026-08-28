# Signed-replica joint jackknife

Run `python3 solve.py --input INPUT.json --output OUTPUT.json`.
The solver requires Python 3 and NumPy, and does not depend on the current
directory or any files other than its input.

Each replica is partitioned independently, retaining partial blocks. The solver
evaluates every expression on signed ratios of channel sums, both on the full
sample and after deleting each block. It implements the contract's exact
count-weighted pseudovalue mean and full covariance, including pooled and
individual-replica results at every requested scale.

Extended-precision arithmetic and centering pseudovalue corrections rather than
large absolute pseudovalues reduce roundoff. Covariance is formed as a weighted
Gram matrix and symmetrized before conversion to finite JSON numbers.

Validation:

- `python3 -m unittest -v test_solve.py` compares with an independent 65-digit
  decimal implementation and checks sign normalization, nonlinear operations,
  unequal replica lengths, partial blocks, covariance, constants, temporal
  blocking, and CLI invocation from another directory.
- `python3 benchmark.py` generates a 120,000-row, eight-channel, six-expression,
  five-replica input with four scales, invokes the CLI, and checks output shapes,
  finiteness, symmetry, and positive semidefiniteness. Its scratch files and
  timing/memory report remain in `benchmark_artifacts/` beside the scripts.
