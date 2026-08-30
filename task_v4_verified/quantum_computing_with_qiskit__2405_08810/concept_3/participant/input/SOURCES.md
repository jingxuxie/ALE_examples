# Provenance and scope

- Ali Javadi-Abhari et al., *Quantum computing with Qiskit*, arXiv:2405.08810, version 3 (June 19, 2024). Sections II.0.6 and III.3 discuss sampling/expectation primitives and near-time classical interaction; Figure 4 and Section IV.3 discuss retargeting toward calibrated partial ZX gates. The paper is motivation, not the source of this synthetic benchmark's noise law or active-design evaluation.
- Qiskit Experiments 0.5.4 official `CrossResonanceHamiltonian` documentation describes the conditional model `(I⊗A+Z⊗B)/2`, duration scans, and target Pauli projections under both control Z preparations. Its analysis documentation relates conditional axes to IX, IZ, ZX, ZZ coefficients. Official `EchoedCrossResonanceHamiltonian` documentation explicitly notes that target-only conditional tomography cannot detect ZI.
- This benchmark adds phase-anchored superposed control preparations and general Pauli readout to make ZI observable; restricts the Hamiltonian to the five published terms; specifies exact global depolarization and a positive-contrast binary meter; and introduces adaptive finite-shot design as an original task extension. It does not depend on the availability of a current Qiskit pulse API.

Stable source locators:

```text
https://arxiv.org/html/2405.08810v3
https://qiskit-community.github.io/qiskit-experiments/stable/0.5/stubs/qiskit_experiments.library.characterization.CrossResonanceHamiltonian.html
https://qiskit-community.github.io/qiskit-experiments/stable/0.8/stubs/qiskit_experiments.library.characterization.CrossResonanceHamiltonianAnalysis.html
https://qiskit-community.github.io/qiskit-experiments/stable/0.5/stubs/qiskit_experiments.library.characterization.EchoedCrossResonanceHamiltonian.html
```
