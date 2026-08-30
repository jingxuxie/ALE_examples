# Branch-correct finite-cutoff Eliashberg solver

Run with the provided NumPy/SciPy environment:

```sh
python solve.py --input instance.npz --output solution.npz
```

The output contains only finite float64 `delta` and `z` arrays. The solver is
self-contained; it does not import the public helper or load auxiliary assets.

## Numerical method

- Positive starting amplitudes and safeguarded Newton steps select the nonzero,
  same-low-frequency-sign branch. High-frequency gaps remain signed.
- Per-patch scaling protects weak induced gaps. Convergence requires a small
  Newton correction as well as a small residual, including near criticality.
- Large problems use degree-11 local interpolation on a logarithmic frequency
  grid with extra nodes near the finite-cutoff boundary. Reduced interaction
  matrices sum the original discrete kernels against the interpolation basis.
- Full-grid cosine/sine transforms evaluate the exact finite convolution.
  Full-grid residuals and reduced-Jacobian defect corrections check and refine
  the interpolated solution before output. No continuum or analytic tail
  replacement is used.
- The normal-state renormalization uses a telescoping discrete sum; nonlinear
  corrections use a cancellation-resistant expression for `w/R - 1`.
- The executable requests one numerical-library thread and includes a CPU-time
  safeguard below the 12-second invocation limit.

## Validation

All nine public examples satisfy the supplied independent operator's residual
criteria, have strictly positive low-frequency gaps, and agree between two
starting amplitudes. Comparisons with separate uncompressed full-grid Newton
solutions have maximum normalized difference below `4.84e-6`.

Fresh invocations also pass with 12-second CPU and 2048-MiB address-space
limits. Public examples take 0.19–0.74 CPU seconds in these measurements.
Public-parameter-derived 40-patch, 32768-frequency stress tests include a
normal-state pairing eigenvalue approximately `1 + 3e-9`; measured CPU times
are below 2.6 seconds, with peak resident memory about 427 MiB.

Detailed measurements are in `validation.json`. These are development checks,
not claims about inaccessible hidden instances or certified hidden solutions.
`isolation.json` contains only the two initial file-open error classes.
