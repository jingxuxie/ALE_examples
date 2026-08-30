# Detector calibration submission

`solution.py` is the complete, standalone JSON-lines entry point. Run it with
`/usr/bin/python3 solution.py`. It requires the supplied Linux x86-64 Python,
NumPy, and SciPy environment. It does not read training data or other participant
files at runtime. Diagnostics go to stderr only.

## Method

- Exact shared-mode, alternate-footprint marginal likelihoods on overlapping
  graph neighborhoods provide fast pilot and intermediate rate estimates.
- Importance-sampled score covariances estimate the information available from
  each action. The information is bounded by the latent complete-data Fisher
  information to avoid optimistic estimates for sparsely sampled events.
- Three adaptive allocations minimize a family-balanced rate-variance objective
  after the initial pilot. Query and shot constraints are enforced throughout.
- A final full-syndrome likelihood fit uses all observations, followed by a
  bounded Gaussian posterior approximation in log-rate coordinates.
- An embedded native Walsh-transform kernel accelerates exact likelihoods and
  gradients. Its readable source is `likelihood.cpp`; no compiler or separate
  library file is required at runtime. A CPU-time guard reserves finalization
  time.

## Validation

All six supplied episodes pass the public protocol tester with 40,000 shots each
and 36–46 queries. Aggregating episodes equally within regime/family cells gives:

- Mean cell log RMSE: **0.04859914**.
- Worst cell log RMSE: **0.07159250**.
- Largest measured worker CPU time in this final public run: **10.467 seconds**.

Additional tests cover 24 sampling-seed/rate perturbations and five constructed
20-detector, 77-channel episodes, including rates near both ends of the bounds.
The maximum-size tests run under hard 60-second CPU and 3-GiB address-space
limits; their largest measured CPU time is **27.644 seconds**.

Likelihood moments and derivatives agree with the supplied exact moment helper
to within `3e-15` on the checked projections. Finite-difference gradient checks
also pass. Public tests are development evidence, not hidden-suite certification.

Individual official reports are `final_report0.json` through
`final_report5.json`; `validation_summary.json` records the aggregate results.
`experiment.py` is a development-only harness and is not imported by the
submission.
