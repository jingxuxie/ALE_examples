# Fermionic spectral recovery

Run the self-contained submission with Python 3, NumPy, and SciPy:

```
python3 solve.py /absolute/path/input.npz /absolute/path/output.npz
```

The solver uses the full observation covariance, the specified six-point
quadrature kernel, bounded physical-family fits, and multiband model averaging.
A positive Gaussian-prior reconstruction stabilizes poorly identified continuum
features. Low-mass intervals combine local fit curvature with calibrated
continuum uncertainty.

The output contains exactly `sample_id`, `spectral_mass`, and
`low_mass_quantiles`. Spectral masses are nonnegative and normalized; identifiers
and row order are preserved. All initialization is deterministic.

Keep `models.py`, `multiband.py`, `recovery.py`, `pool_projected.npz`, and
`gp_prior.npz` beside `solve.py`. No training labels or public asset paths are
needed during prediction. BLAS thread counts are fixed to one before importing
NumPy and SciPy.

Public validation scores are recorded in `validation_report.json`. The local
one-CPU benchmark, run with a 2 GiB address-space limit, is recorded in
`resource_report.json`.

The 192-case public validation batch scores **96.22 core** and **89.71 worst
family**. The final local resource check takes approximately **54 seconds** and
uses approximately **70 MiB peak resident memory**.

On Linux, repeat the resource check with:

```
python3 benchmark.py /absolute/path/input.npz /absolute/path/output.npz
```
