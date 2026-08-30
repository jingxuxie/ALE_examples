# EPW hardness discovery, 2026-08-28

## Sources inspected

- Seed: https://arxiv.org/abs/1604.03525 and its v2 PDF, particularly polar interpolation, anisotropic Eliashberg theory, spectral functions, and transport.
- Follow-up: https://arxiv.org/abs/2302.08085 (transport and anisotropic multi-band developments).
- Official theory: https://docs.epw-code.org/Theory.html
- Official source: https://github.com/QEF/q-e/tree/develop/EPW ; `EPW/src/transport.f90`, `EPW/src/supercond.f90`.
- Release history: https://docs.epw-code.org/Releases.html ; polar/interpolation corrections and iterative transport population fixes motivate tests of physical invariants rather than package reproduction.
- Public issue discussion: https://forum.epw-code.org/viewtopic.php?f=3&t=1319 ; long-range summation limits and superconducting memory handling.
- Prior local EPW package under `tasks/`: artificial two-stage transport triage. The prior reference passed, but the fresh failure was missing output at a 600-second deadline. It is not retained here as substantive hardness evidence.

## Candidate inventory

1. **Hidden spectral prediction (D), selected.** Infer physical positive electron-phonon spectra and derived quantities from finite noisy imaginary-axis observations. Competing resolutions and noise structures make it a statistical inverse problem, not evaluation of a supplied formula.
2. **Multi-temperature collision-event coresets (A), selected.** A single nonnegative, sparse event reweighting must preserve microscopic rates, harmonic dissipation, and nonlinear inverse-operator transport across temperatures and distinct scattering geometries. Sparse linear algebra alone does not solve the selection problem.
3. **Matched-observable transport falsification (B), selected.** Find smooth reciprocal scattering models indistinguishable by linewidth and low-order transport data yet different under the full collision equation. Matching the full projected tensor removes the trivial rotational-anisotropy example.
4. **Active Matsubara experiment design (E).** Budgeted adaptive frequency probes for low-energy spectral discrimination. Deferred because limited-query identifiability is harder to validate than fixed held-out prediction in this session.
5. **Anisotropic superconducting design witness (C).** Equal isotropic alpha-squared-F and constrained row couplings but different superconducting transitions. Deferred: unconstrained anisotropy admits trivial block constructions, while stronger constraints need an expensive trustworthy finite-cutoff critical-temperature certificate.
6. **Gauge-covariant polar interpolation repair (F).** Repair degenerate-subspace transport and long-range separation in an actual reduced multi-file workflow. Deferred: likely devolves into implementing known covariance identities or reproducing official fixes.
7. **Magnetic-field collision solver improvement (A).** Robust preconditioned transport in nearly conserved subspaces. Rejected in isolation because a standard Krylov solver/preconditioner can be the entire solution.
8. **Polar singular quadrature improvement (A).** Hidden anisotropic near-threshold Brillouin-zone integrals under an evaluation budget. Deferred: a fairly standard singularity subtraction plus adaptive quadrature could dominate.
9. **Causal analytic-continuation witness (C).** Construct positive spectra satisfying noisy imaginary-axis data and physical sum rules. Deferred as a standalone concept because feasibility can collapse to a linear program; prediction forces useful recovery rather than arbitrary feasibility.

## Selection rules

Exactly three concepts will be built, using three primary verification modes. Targets are fixed before fresh solving attempts. All model systems are explicitly reduced physically admissible models, not claims of new ab-initio EPW calculations or experimentally measured materials. Hidden data, private search, past submissions, evaluators, and research notes remain outside participant mounts. A truth-label evaluation validates scoring but does not demonstrate an implementable solution to a hidden prediction problem. No failure attributable solely to runner or evaluator infrastructure is counted as empirical hardness.
