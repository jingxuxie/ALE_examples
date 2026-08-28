# Sidecar: executable-reference priorities

Research date: 2026-08-27. Research only: no pilots, reference simulations, builds, or participants have been run by this sidecar. Main owns `private/sources/ALPS`; this sidecar reads its history without changing its checkout.

## Immediate handoff

1. **Realistic-scale Hubbard ladder: strongest scientific gap, expensive reference.** Official later MPS application exists at ALPS commit `34688482fbc09fe7d359987f3e1e223fa07bfcb2` (2014-10-14); first import is `006cbc8ef2bc3e6abc080c0bc015b1a105751b0d` (2014-01-09). Use TeNPy's existing `FermiHubbardModel` plus DMRG as an independent reference if legacy ALPS MPS compilation is impractical. The paper's 192-site, doped ladder needs correlation convergence, not merely accurate energy. Its largest calculation took 46 hours on five historical cores; do not promise a one-hour reference or silently reduce it to ED scale. Reference inputs and pair-field operators are in arXiv ancillary files. Source: <https://arxiv.org/abs/1407.0872v2>; independent implementation documentation: <https://tenpy.readthedocs.io/en/latest/reference/tenpy.models.hubbard.FermiHubbardModel.html>.

2. **Physical-family transfer to parity-only superconducting fermions: fastest MPS-based reference prospect, conditional hardening.** Actual official Z2 fixes are `4ef7add8c6ea9cb3b1bf747a7af262a5cdd96074` and `6708c330388a4aec3fb8a5dd9c0ce8a43f77b213` (2014-06-19). The MPS paper supplies `z2_example/kitaev.py` and `z2_example/tsc.xml`. A free Kitaev chain alone is NOT hard: BdG diagonalization solves it. Any retained concept must include genuinely interacting parity-conserving physics and independently score anomalous correlations, parity-sector handling, and ground/excited-state convergence. Interaction reference code and exact artifacts are still being checked. Do not claim the paper's free example demonstrates interacting-reference feasibility by itself.

3. **QMC integration/performance: real later worm implementation, not a new generic kernel.** Sadoune–Pollet 2022 supplies runnable code, parameters, ED tests, and published figure data: <https://arxiv.org/abs/2204.12262>, <https://github.com/LodePollet/worm>. A credible task couples continuous-time event topology and mixing with winding/Green-function estimators, uncertainty calibration, and checkpoint/MPI aggregation. Merely implementing a small stochastic matrix or fitting QMC output is insufficient. Dependency risk: ALPSCore, Boost, HDF5 and MPI. Official ALPS DWA history also has a concrete 2012 data-structure rewrite (`0ba2b7366ac89bafb47a96d1faacf2ca88940bcc`) and 2013 measurement/trap improvements. Details and fixed source pins follow in the complete brief.

4. **Real-data model mismatch: do not count as build-ready yet.** A promising genuine dataset is the 2021 ALPS-citing experiment *Realization of a bosonic antiferromagnet*, <https://www.nature.com/articles/s41567-021-01277-1>, with data DOI <https://doi.org/10.7910/DVN/GPMPMP>. The paper says its custom Python simulation code is available only upon request. Need to inspect whether the deposited files contain enough actual observations AND privileged theoretical outputs to support a defensible held-out predictive score. A published curve or unavailable author code is not an executable reference. No synthetic surrogate should be mislabeled real experimental mismatch.

## Exact old public starting point already located

Official history contains `09e558e0b7a3a19c68893fa39254d0a639b05392`, dated 2011-01-08, message `Final ALPS 2.0 release?` (question mark is literally upstream). This is a precise release-era candidate, not a verified release tag. Use an exported tree rather than a git checkout with later objects reachable. URL: <https://github.com/ALPSim/ALPS/commit/09e558e0b7a3a19c68893fa39254d0a639b05392>.

**Important negative:** the rewritten `dirloop_sse` is already part of ALPS 2.0, and generalized directed-loop theory predates it. Neither is a later private solution relative to a 2.0 public baseline. Likewise, do not use modern ALPS HEAD as the old public artifact; it contains later behavior and does not even have the same application layout.

## Ready code versus unverified execution

These are source-feasibility priorities, not performance measurements. Local `numpy` and `scipy` are present; `tenpy` is not installed in the inspected Python environment. No successful compile, numerical convergence, runtime, or participant score is asserted here.
