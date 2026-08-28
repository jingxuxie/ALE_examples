# Solution

`solve.py INPUT.npz OUTPUT.npz` produces all four required arrays using NumPy.

- Analytically differentiates the short-range Fourier phases, accumulating
  repeated atom blocks and applying the Hermitian part.
- Analytically differentiates both Born-charge factors, the dielectric
  denominator, and Gaussian reciprocal weight. The phase depends only on the
  supplied reciprocal vector. All supplied vectors are summed in bounded chunks;
  no finite-difference step, reciprocal cutoff, or additional subtraction is used.
- Converts reduced matrix derivatives to Cartesian coordinates with `cell.T`,
  projects with complex-adjoint eigenvectors, and retains full within-group
  response operators with the specified mean-eigenvalue normalization.
- Diagonalizes each directional operator independently. Cartesian branch
  velocities use that same eigenbasis; successive-gap tied clusters receive
  component-wise trace averages. Inactive and cross-group entries remain zero.

## Validation

Ran `python validate.py` successfully, using public smoke data and deterministic
synthetic cases. Also ran the required two-path CLI on the smoke input and checked
output shapes, dtypes, finiteness, and Hermiticity.

- Smoke derivatives agree with independent five-point finite differences to
  approximately `4.1e-12` relative error.
- Anisotropic, oblique-frame cases include queries `2.1e-5` from zero and nonzero
  reciprocal singularities. The polar derivative agrees with an independent
  extended-precision analytic formula to `6.4e-16` relative error; finite-difference
  checks for full and short-range-only derivatives remain below `3e-9`.
- Verified complex group-basis covariance, invariant directional spectra and
  branch vectors, active singletons, inactive groups, exact ties, and transitive
  adjacent-gap ties against independently constructed response operators.
- Verified chunked accumulation over 15,625 reciprocal vectors. Local compute
  timings were approximately 1.91 seconds for 96 derivative queries with 16 atoms
  and 1,331 reciprocal vectors, and 0.49 seconds for 512 response packets with
  12 modes and 14 directions. These are local measurements, not grader results.
