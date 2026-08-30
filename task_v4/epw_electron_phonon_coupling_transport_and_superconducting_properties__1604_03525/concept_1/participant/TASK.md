# Recover the phonon spectrum

**PRIMARY MODE D — hidden prediction.** Infer nonnegative isotropic Eliashberg
spectra from finite, noisy bosonic-Matsubara interaction measurements in a warm,
weak-coupling operating regime. This is
an inverse problem, not a forward-formula exercise. Preserve low-energy coupling
and superconductivity-relevant moments without inventing unresolved sharp peaks.

`input/` contains 8,192 labeled training and 512 labeled validation examples,
the exact schema, forward/noise model, family descriptions, and scoring rule.
`workspace/` contains public forward and scoring utilities. `baseline/solve.py`
is a runnable covariance-aware nonnegative regularized inversion.

Submit a directory containing `solve.py` and any offline-trained assets. It runs
as `python solve.py --input observations.npz --output prediction.npz` once for
the entire hidden batch. Return only `alpha2f`, a finite nonnegative `[B,192]`
array, in original row order. See `input/SCHEMA.md` for the complete contract.

Hidden evaluation balances four disclosed spectral families, with independent
spectra, temperatures, missing observations and correlated noise. Scores combine
spectral Wasserstein distances and errors in coupling, logarithmic frequency,
and the specified approximate critical temperature; all properties are derived
from your spectrum. **Pass: core score ≥80 and worst-family score ≥70.**

Offline training is allowed. Inference: one CPU machine, at most four threads,
3 GiB memory, no network/GPU, 110 seconds for the solver and 120 seconds for the
whole evaluation. Only the staged submission and observation file are readable.
Do not include validation labels as hidden answers. No report is required.
