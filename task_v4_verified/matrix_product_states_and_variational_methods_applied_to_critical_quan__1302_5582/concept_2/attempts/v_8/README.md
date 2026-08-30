# Critical Ising uniform MPS

The submission is `state.npz`. It contains only a real float64 array `A` of
shape `(2, 24, 24)`. The accompanying `verification.json` records the public
checker's full results, and `verification_summary.json` contains its compact
summary. Only `state.npz` is needed for evaluation.

## Construction

The supplied bond-24 baseline was refined directly against the exact public
observables. The physical tensors retain the prescribed virtual parity blocks.
Each block row is normalized using a differentiable Cholesky factorization,
enforcing right canonical form rather than penalizing its defect.

The real transfer map is represented in orthonormal even-symmetric,
odd-symmetric, and odd-antisymmetric matrix bases. Its thermodynamic stationary
density is obtained by a trace-constrained linear solve. Binary transfer powers
evaluate the long-distance two-point functions and all specified interval
configurations. PyTorch differentiates these calculations in float64, and
SciPy L-BFGS-B optimizes the tensor parameters.

For an interval of length `length`, its pair insertion is
`M = E_X E^(length-1) E_X`, and its measured mean is `m = tr(rho M(I))`.
The centered insertion is `M - m E^(length+1)`. Contracting two or three such
insertions gives the covariance or third cumulant with the submitted state's
own means and lower moments. No exact-state factorization is imposed on the
submitted tensor.

The differentiable contractions were checked against the supplied literal
full-tensor checker on the baseline. Absolute discrepancies were below
`5e-14` across every observable, including all 252 cumulants. The loss gradient
was also checked by centered finite differences. Training uses a multiscale
sample of two-point distances and every quartet and sextuple; final public
validation checks every required distance.

## Files and commands

- `optimize.py`: differentiable contractions and optimization driver.
- `max_start.npz`: checkpoint used to initialize the final refinement.
- `minimax.log` and `minimax.jsonl`: refinement diagnostics; reported errors are
  divided by their contractual tolerances.
- `verify.py`: compact wrapper around the unmodified supplied public checker.
- `implementation_agreement.json`: baseline contraction cross-check errors.

From this directory, the unmodified public check is:

```sh
python ../../participant/workspace/check.py state.npz
```

To run the refinement from its saved starting tensor:

```sh
python optimize.py --input max_start.npz --prefix reproduced --mode max --iterations 1600
```

The submitted checkpoint was selected before this iteration limit once all
families passed with substantial margin, then independently checked using the
unmodified public checker. Its SHA-256 and measured errors are recorded in
`verification_summary.json`.

All construction uses only the provided participant assets and installed CPU
NumPy, SciPy, and PyTorch libraries.
