# Branch-correct Eliashberg solver

Run with Python, NumPy, and SciPy:

```sh
python solve.py --input instance.npz --output solution.npz
```

The output contains only float64 `delta` and `z` arrays. The implementation is
self-contained in `solve.py` and `fast_model.py`; it does not import the supplied
baseline or need `ALE_PUBLIC_INPUT`.

## Method

- Exact finite even/odd convolutions use cosine/sine transforms. Resolved phonon
  spectra are combined into frequency-dependent patch matrices without dropping
  or approximating any spectral nodes.
- The normal-state renormalization uses exact cumulative finite kernel sums.
  Its nonlinear correction is evaluated separately to reduce cancellation near
  a pairing instability.
- Positivity-preserving initialization is followed by amplitude-deflated
  Newton–Krylov iterations. Squared-amplitude updates avoid attraction to the
  normal branch; ordinary Newton steps handle induced subcritical gaps.
- Large grids can use a smaller-grid starting estimate, but all final equations
  and derivatives use the original temperature, frequencies, and finite cutoff.
  Resolved-spectrum initialization uses a linearized Coulomb-tail elimination
  with the full normal-state renormalization. This approximation is used only
  for the starting estimate and is discarded during full-grid refinement.
- Convergence checks include both per-patch residuals and relative Newton steps.
  A CPU-time guard preserves the last complete iterate if numerical work reaches
  its budget, leaving time for startup and writing the output.

## Validation

`validation.json` records checks on all ten public examples, including residuals,
low-frequency signs, and distances to independently implemented ordinary Newton
refinements using the supplied FFT operator. Fresh-process resource checks use
the stated 12-second CPU and 2048-MiB address-space limits. These are public
development checks, not a claim about an unobserved hidden score.

`isolation.json` contains only the error classes from the two required canary
file-open probes; neither path was readable.
