# Correlated Hubbard gap predictor

Run the submission with:

```sh
python3 solver.py request.json predictions.json
```

The request and prediction formats follow the supplied task schema. All model
and native-library paths resolve relative to this directory. Inference uses
NumPy, SciPy, the standard library, and the accompanying precompiled libraries;
it does not launch processes, create worker threads, or access the network.

The predictor uses direct Lanczos sector solves for ten-site clusters and
physics-informed Gaussian-process predictions for twelve-site clusters.
Remaining runtime is used for uncertainty-ranked numerical refinements.
Native CPU and wall-clock guards preserve time for writing the result.

Training uses 1,792 supplied public labels and 3,840 additional examples from
the supplied generator and exact solver. The final fit includes validation
labels. Before that final refit, the independent public validation run has
charge RMSE 0.02812 and spin-sector RMSE 0.01366; every family also passes its
limits. See `dev/hybrid80_score.json` for the pre-refit accuracy report and
`dev/inference80.log` for its 25-second/2-GiB constrained execution.

Development scripts and reports are retained in this directory and `dev/`.
None of them is invoked during inference. The native source files accompany
their precompiled shared libraries; inference does not require a compiler.

`isolation_audit.json` records the required initial access check.
