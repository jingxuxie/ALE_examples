# Extremal mixed-matrix spectrum recovery

Run the standalone solver with one JSON case on standard input:

```sh
python solve.py < case.json > result.json
```

The `output/` directory contains an identical standalone entry point, matching
the task's requested directory layout. The only non-standard dependency is
mpmath, supplied by the task environment. No network access, subprocesses,
external data, persistent state, or additional packages are used by the solver.

## Method

1. Convert the exact decimal Chebyshev coefficients into primitive integer
   power-basis matrices and form their determinant exactly.
2. Compute polynomial GCDs using finite-field Euclidean algorithms, Chinese
   remaindering, and exact divisibility certificates. Recover the square-free
   repeated-root support. An interior zero of a nonnegative determinant must
   be repeated; endpoints and isolated points are checked separately and exactly.
3. Isolate every real contact using exact integer Bernstein coefficients and
   Descartes sign variations. This distinguishes touching zeros from arbitrarily
   small strictly positive minima without numerical thresholding.
4. Refine each isolated contact in its own rescaled coordinate at adaptive
   arbitrary precision. Construct a normalized null projector from the better
   conditioned matrix row.
5. Evaluate all coupled moment equations and solve the row-scaled full-rank
   system with high-precision Householder QR. Serialize decimal strings, with
   extra coordinate digits when a large origin conceals a small local scale.

## Validation

Both provided samples pass independent checks of projector normalization,
functional null residuals, positive weights, and global moment residuals.
The recovered sample spectra contain 11 and 14 atoms respectively.
Fresh-process checks take 0.74 and 0.98 seconds, with approximately 17 MiB peak
memory; the maximum relative moment residual is below 5e-238.

Additional deterministic synthetic tests cover 1e-10 gaps, degree-64 matrices,
high-order contacts, close nonreal roots, rapidly rotating null spaces,
32 coupled atoms, a 32-atom cluster, and coordinate exponent gaps of 1200.
The modular GCD implementation was also compared with an independent exact
implementation on 80 randomized polynomial pairs. These checks do not use
hidden evaluation data.

Development checks are available as `stress.py`, `adversarial.py`, and
`validate.py`; they are not needed to run the submission.
