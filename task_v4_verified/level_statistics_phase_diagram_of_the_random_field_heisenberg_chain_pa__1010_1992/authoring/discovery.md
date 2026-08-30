# Generation-time concept selection

The paper is Pal and Huse, *The many-body localization phase transition*, arXiv:1010.1992 (2010). The user's descriptive title denotes its level-statistics protocol, not the bibliographic title. The organizer inspected the original PDF, including the periodic spin-1/2 convention, zero-magnetization sector, middle rank-third restriction, adjacent-gap ratio, and Eq. (6) dynamical fraction. No task asserts that finite L demonstrates an asymptotic transition.

## Concepts considered before fresh testing

1. **Large interior eigensolver throughput (A).** Rejected: a standard shift-invert implementation is too close to a complete recipe. Source-native solvers already address the core algorithm.
2. **Hamiltonian convention recovery plus audit certificate (F/A).** Rejected: same-paper prior task has two isolated 100/100 submissions, including the structurally hardened certificate variant. The successful solution and evaluator were inspected, not given to new agents.
3. **Sample-specific dynamical-fraction surrogate (D), concept_1.** Selected: accurate finite-realization prediction across spatial disorder correlations under an inference budget requires learning nonlocal many-body resonance effects rather than diagonalizing each test case.
4. **Spectrally matched disorder layouts (C), concept_2.** Selected: constrained permutation design must jointly preserve the field histogram, match spectral statistics, separate spin relaxation, and withstand calibration perturbations. The finite-size scientific question is diagnostic sufficiency, not thermodynamic phase labeling.
5. **Robust spectral-window counterexample (B), concept_3.** Selected: falsify a supplied finite-spectrum representativeness claim with nondegenerate bounded disorder and a persistent discrepancy, not a one-off tiny-window fluctuation. The original paper's protocol is the control, not the claim under attack.
6. **Finite-size crossing active design (E).** Deferred: target choice can confound sampling error with uncontrolled thermodynamic extrapolation; a clean exact finite target still risks being ordinary noisy bisection.
7. **Cooperative three-site intervention (E/B).** Deferred: promising non-additive search over 299 supports with a 40-query budget, but requires an API preventing direct uncounted diagonalization and a separately verified witness-yield study. No fourth concept was built.
8. **Monotonic-disorder falsification (B).** Rejected: weak-disorder integrability and sample fluctuations make an unconstrained example too easy.
9. **Missing-level spectral reconstruction (A/D).** Rejected: without a reliable observation model, the inverse problem may be underdetermined rather than capability-hard.
10. **Upstream symmetry-projector repair (F).** Deferred: current QuSpin issues motivate independent symmetry checks, but importing a known patch is not the desired scientific asymmetry.

## Privileges and separation

Generation uses private exact diagonalization, broad disorder/permutation banks, independent full-space Hamiltonian checks, and private held-out perturbations. Tested agents receive only their concept's participant tree and an initially empty output directory through the required allowlist runner. Generator scripts, hidden seeds/labels, sibling concepts, source notes, prior submissions, other fresh transcripts, evaluator code, and privileged candidates are outside that allowlist. The inference evaluator additionally executes untrusted prediction code inside an explicit filesystem/network sandbox. Static design and counterexample evaluators parse JSON and never execute submitted code.

All primary targets are fixed and hashed before the corresponding fresh launch. No failing attempt is used to change a target. Successful attempts trigger private stress testing and, only if a genuine failure is found, a new frozen generation followed by a completely fresh run. Open targets are explicitly allowed; lack of a passing known implementation is not silently equated to impossibility or achievability.

## Inspected primary sources and local artifacts

- https://arxiv.org/abs/1010.1992, its PDF, and archived original TeX source: model and observables. The source explicitly states periodic boundaries, the middle one-third energy-ranked sample, and the per-eigenstate dynamical fraction; the source archive is retained under `authoring/sources/`.
- https://arxiv.org/abs/1411.0660: energy-resolved extension and multiple diagnostics; source text emphasizes realization-level aggregation rather than treating eigenstates as independent disorder samples.
- https://arxiv.org/abs/1803.05395: shift-invert implementation and numerical efficiency/reliability. The linked Bitbucket repository was attempted but did not expose source through the browsing interface.
- https://arxiv.org/abs/2301.11132: finite-chain sample-to-sample gap-ratio fluctuations; motivates keeping realization variation separate from ensemble claims.
- https://raw.githubusercontent.com/QuSpin/QuSpin/master/examples/scripts/example0.py: inspected exact diagonalization example, spin normalization, magnetization restriction, and interior eigenvalue API. This example's parity choice is not valid for generic random fields and is not copied into our model.
- https://github.com/QuSpin/QuSpin/issues and releases: inspected the issue index, issue 763 (multi-Nup projectors), and release history. The archived API snapshots additionally include issue 773 (Majorana Hermiticity checks), issue 776 (integer-to-state ambiguity), and the April 2026 documentation commits. These motivate independent checks, not a copied upstream patch or hidden answer.
- Local `tasks/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/status.json`, `participant/v_02/TASK.md`, `solution/v_02/solve.py`: previous rejected benchmark and successful formula/certificate solution.
- Local `tasks_v4/black_holes_and_random_matrices__1611_04650/authoring/run_attempt.py`: inspected prior isolation/timeout bookkeeping pattern; no private answer content is supplied to fresh agents.

No external raw measurement dataset or original paper supplement was available as a separate retrieved artifact. New labels are exact simulated finite-chain outcomes, with generation provenance archived privately.
