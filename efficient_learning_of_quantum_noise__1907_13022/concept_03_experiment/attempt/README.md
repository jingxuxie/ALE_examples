# Calibration-noise solver

Run the self-contained submission with:

```sh
python solver.py INPUT.npz OUTPUT.npz
```

Only `solver.py` is required. It uses NumPy and SciPy, with no external data,
trained parameters, or development-module imports.

The solver transforms each shot-normalized acquisition into parity modes and
fits a separate geometric decay and nuisance SPAM amplitude. It uses the
actual depths and shot totals, robust residual weights, and a mode-dependent
fitting window that excludes nearly vanished tails. Reliable alternating
parities can identify negative channel eigenvalues. An uncertainty-weighted
convex projection enforces a nonnegative, normalized one-cycle distribution.

Group correlations use OR events, whereas conditional information uses full
categorical bit-vector marginals. Conditional information is in nats. The
spatial diagnostic constructs the complete normalized DAG distribution,
including fair conditionals for absent parent configurations, and returns
the base-two Jensen–Shannon distance.

Validation:

```sh
python -m unittest -v test_solver.py
python development.py
```

The development scripts generate their own synthetic channels. They are not
needed for inference and are not part of the staged submission.
