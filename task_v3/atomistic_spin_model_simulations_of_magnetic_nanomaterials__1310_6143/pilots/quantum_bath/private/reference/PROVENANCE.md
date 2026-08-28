# Privileged reference provenance

Official repository: https://github.com/richard-evans/vampire
Pinned quantum branch: `004271743c3691717ac7ddb766991e75f9a0e98d`.
The original `src/quantum/noise.cpp` and `src/quantum/llg.cpp` are preserved in
this private directory. The spin/memory differential equations and material bath
spectra in `solve.py` are dimensionless adaptations of these implementations.
Related author method: https://arxiv.org/abs/2508.11315 and data archive
https://zenodo.org/records/18391022.

The upstream branch is not claimed to compile unmodified: at the pinned head the
material argument was added to `spinDynamics` without all call sites being
updated. This pilot uses an explicitly documented equation-level port, not a
fabricated claim that the whole upstream executable passed. It regularizes the
zero-temperature spectral limit analytically instead of inheriting a finite
temperature fallback in upstream code. The participant contract fixes a finite
Gaussian forcing record so integration errors can be evaluated without stochastic
sampling noise. The benchmark geometries and records are newly generated; they
are not experimental Ni/Gd observations or author-provided trajectories.

Independent checks in `independent_validation.json` compare against a separately
implemented SciPy DOP853 vector field, time-step refinement, and the zero-noise
limit. Stored references are generated before any pilot attempt. Their physical
scale includes 46,656 independently forced spins, exceeding the 45,000-spin
example in the adjacent contribution. Small systems are used only for oracle
validation, not as a substitute for the large hidden execution cases.

The public baseline retains geometry, local fields and classical damped
relaxation. It has no colored-noise generation or causal memory state. Neither
this directory, the upstream source, nor generated targets is participant-visible.
