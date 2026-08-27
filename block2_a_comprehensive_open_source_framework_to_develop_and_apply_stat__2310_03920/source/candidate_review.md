# Private concept review

Source inspected: arXiv 2310.03920v2; official block2-preview source,
custom-Hamiltonian and Hubbard tutorials, high-level driver and tests; official
block2-example-data SIAM, UEG, Fe2OCl6 and plotting workflows. Paper and this
review must never enter the participant mount.

## 1. Transport pipeline reliability across changing conservation laws (pilot)

- Contribution: complex MPS time evolution, general MPO/custom local spaces,
  symmetry-aware state preparation; empirical nonequilibrium SIAM current and
  the engineering claim that one framework supports qualitatively different
  Hamiltonians.
- Artifact: extracted official SIAM model preparation and time-evolution
  workflow, installed official numerical engine, custom Hubbard-Holstein
  operator definitions; benchmark-owned integration code around these assets.
- Decisions: representation/ordering versus truncation as the source of a
  discrepancy; usable symmetries versus general representation; state-preparation
  and propagation error budgets; separating transport current from pairing
  sources in the continuity equation. Each has plausible but inequivalent
  choices, testable by small exact cases, continuity and refinement.
- Loop: reproduce stock run, contrast gauge/layout/refinement diagnostics,
  repair assembly or numerical policy, rerun, compare independent observables.
- Public evidence: tiny exact dimer, unlabeled development problems from each
  supported physical class, invariants and small-system diagnostic tooling.
- Hidden families: interacting impurity chain, frustrated Hubbard ladder,
  spin-orbit flux ring, superconducting paired wire, electron-phonon contact.
  These change geometry, conservation laws and local Hilbert space, not seeds.
- Evaluation: trajectory accuracy, worst-family accuracy, runtime/memory,
  independently rerun evidence and continuity; continuous relative scoring.
- Shortcut risk: exact diagonalization on small cases; blindly call td_dmrg;
  copy SIAM script. Use physically nontrivial sizes and real shifted symmetries,
  not a tiny common Pauli-array interface. No full public trajectory oracle.
- Why pilot: numerical engine alone does not define correct Hamiltonians,
  state sectors, observables, or resource policies across these regimes. It
  could still be easy for a frontier agent; empirical screening decides.

## 2. Finite-temperature UEG thermodynamics and susceptibility (reject prebuild)

- Contribution/claim: purification and grand canonical ensemble, UEG thermal
  energy and particle fluctuations. Real official 07-UEG script.
- Decisions: ensemble, chemical potential calibration, imaginary-time budget.
- Loop/evidence: beta-step refinement and fluctuation identities; tiny exact
  spectra. Families: UEG, Hubbard, molecular active space.
- Score: equation-of-state accuracy, thermodynamic consistency, compute.
- Shortcut: the supplied official ancilla and td_dmrg calls essentially solve
  all three classes. Extending the same recipe to more inputs is not research.

## 3. Non-Hermitian downfolded spin-gap validation (reserve)

- Contribution/claim: arbitrary higher-body MPOs and non-Hermitian DMRG;
  similarity-transformed Fe-cluster spin gaps. Real 05-Fe2OCl6 CC/normal-order/
  DMRG multi-file pipeline, but expensive missing intermediate tensors.
- Decisions: truncation of induced operators, root tracking, left/right-state
  diagnostics versus discarded-weight extrapolation.
- Loop/evidence: reconstruct small active spaces, compare physical gaps and
  non-Hermitian residuals, revise downfolding and sweeps. Families: Fe cluster,
  molecular dissociation, transcorrelated lattice.
- Score: spin gaps, residuals, cost, extrapolation validity.
- Shortcut risk: generic eigs on small downfoldings; already supported driver
  for large ones. Not selected without reconstructable cheap independent truth.

## 4. Orbital rotation of entangled MPS (reject prebuild)

- Contribution/claim: MPS representation transforms and finite-bond rotation
  stability. Real driver and rotation utilities.
- Decisions: logarithm branch, matching/phase gauge, truncation allocation.
- Loop/evidence: rotate/invert and compare RDMs; families: localized molecular,
  spin-mixed orbitals, delocalized periodic orbitals.
- Score: state fidelity, RDM accuracy, memory/runtime.
- Shortcut: a standard fermionic Givens/swap network provides the same solution
  throughout; most apparent difficulty would be code volume or conventions.

## 5. Automatic MPO compression/performance selection (reject prebuild)

- Contribution/claim: general MPO construction and efficient large operators;
  real FastBipartite/SVD/NC code and molecular/lattice/Holstein assets.
- Decisions: ordering, cutoff, symbolic versus numerical compression.
- Loop/evidence: compare expectation errors, bond dimensions and timing.
- Families: ab-initio integrals, long-range spin model, vibronic operators.
- Score: errors, contraction work, memory.
- Shortcut: invoking the existing construction variants and picking a Pareto
  point is ordinary parameter search unless modifying the C++ internals, which
  risks turning the pilot into a build-time rather than scientific challenge.

Only concept 1 is authorized for pilot construction at this stage. No empirical
hardness claim is made by this document.
