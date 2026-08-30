# Private provenance and design record

This file and all hidden generators, controls, labels and authoring diagnostics
are excluded from participant mounts. No upstream implementation was copied.

## Paper seed

ALF collaboration, *The ALF (Algorithms for Lattice Fermions) project release
2.0: Documentation of the auxiliary-field quantum Monte Carlo code*,
arXiv:2012.11914v2, January 18, 2021. The version is deliberately pinned;
later releases are not silently attributed to release 2.0.

Primary paper: `https://arxiv.org/pdf/2012.11914v2`.
Parent artifact: `../research/paper_v2.pdf` relative to concept_3 root.
SHA256: `60918e5100e76eb09039826d5d85e2481869915e3264b323fb4038cf24776714`.
The stochastic maximum-entropy/analytic-continuation material motivates the
positive sum-rule-constrained spectral inverse problem, the fermionic
imaginary-time kernel and covariance-weighted misfit. Our data are synthetic
spectral models, not ALF-generated Monte Carlo runs or exact Hubbard solutions.

## Official repository context

Official repository: `https://github.com/ALF-QMC/ALF`.
Parent inspection commit: `f81b5cbc74b098b3910cc22e6d31b918be1e1223`.
Access date: August 28, 2026. Parent `research/provenance.json`,
`research/files.json`, `research/issues.json`, `research/CHANGELOG.md` and
`research/maxent.tex` record the source inspection; they are not participant
assets. The later MaxEnt documentation was inspected for conceptual context,
not misrepresented as the release-2.0 text.

- Issue 631, NaNs at large beta*omega, and PR 632, kernel overflow protection:
  stable log-add-exp forward kernels, with an extreme-beta numerical control.
- PR 395, covariance Cholesky versus eigendecomposition and non-PD test inputs:
  supplied covariances are constructed SPD, verified for every public and
  hidden row, and explicitly mean covariance of the observed vector.
- January 25, 2024 changelog: classic and stochastic analytic continuation,
  default models and particle-hole-symmetric channel are later developments.
- February 1, 2024 changelog: arbitrary spectral-function integrals motivate
  evaluation of physically interpretable spectral masses and band integrals.

These issue notes motivate robust task design, not exact upstream regressions.
No upstream Fortran, full documentation, repository archive, or issue body was
copied into concept_3. The private Python generator and benchmark are original.

## Frozen experiment

The generator creates independent training/validation/heldout SeedSequences,
with separate spectrum, observation, shuffle and opaque-ID streams. The hidden
split was fixed before validation calibration and is pinned by manifest SHA256
`8e405034f1ab12b88c609de33a84d0063d485e8993ef1aa45c2a906d6fd951bd`.
Calibration used only public validation labels and a private known-component
shape diagnostic on validation, never the heldout scores. Targets 90 core and
85 worst-family were frozen before fresh participant attempts. The heldout
baseline subsequently scored 75.2338563236265 / 48.73553181385645 in 9.647069
seconds of evaluator-measured wall time and does not pass.

The oracle-label artifact is constructed and scored entirely inside trusted
test code. It is an evaluator positive control, NOT a submitted executable,
NOT a prediction method, and NOT evidence that the target is achievable from
noisy observations. The known-shape diagnostic has unavailable latent component
shapes and likewise does not demonstrate prediction achievability. No
information-theoretic impossibility is claimed. Parent owns fresh evaluations,
champion selection and final difficulty/status conclusions.

## Runner diagnostic qualification

Wall time is authoritative and independently measured by the evaluator around
the complete sandboxed invocation. Historical calibration and baseline reports
used keys `cpu_seconds` / `peak_rss_bytes` for bubblewrap wait4 rusage. These
values describe the launcher, not reliably aggregate descendant Python usage.
Reports have been relabeled without changing measured values. The current evaluator names them `launcher_cpu_seconds` and
`launcher_peak_rss_bytes` with an explicit scope field. No score or pass
decision depends on these launcher diagnostics. One-core affinity and inherited
2 GiB per-process RLIMIT_AS are enforced. No aggregate-memory claim is made.
