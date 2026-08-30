# XDiag hardness discovery, 2026-08-28

Generation inspected arXiv:2505.02901v3; official XDiag source at
`d7296fa258dadb79c27512813497125151c0210c`; recent commits, releases, and
issues (including 108 and 115); and the previous local Sector Relay II
task, exact solver, and empirical status. Downloads are in `sources/`.
The paper's fixed-magnetization blocks, permutation-sector measurements,
interacting spin dynamics, and exact expectation values seed the tasks.
The official package is a generation resource, not a participant dependency.

## Considered concepts

1. **Minimax adaptive symmetry-diagnostic fleet optimization (A), selected.**
   Reuse independently validated quantum instruments from a previous successful
   solver, but optimize limited shared hardware, feedback, and capacities across
   a larger fleet. Discrete adaptation and minimax resource coupling make this
   more than implementing the spin Hamiltonian or one eigensolver.
2. **Robust many-body pulse compilation (C), selected.** Recover bounded controls
   realizing a common multi-state transformation across drift calibrations. An
   undisclosed generating pulse demonstrates feasibility; any valid pulse wins.
   Noncommuting controls and simultaneous state constraints create a genuinely
   nonlinear search, not reconstruction of a source package.
3. **Active interacting-spin spectroscopy (E), selected.** Choose finite-shot
   quenches and coherent interventions to recover exchange, fields, frustration,
   anisotropy, and readout errors with a strict experiment budget. Parameter
   ambiguity, experiment selection, nonlinear inference, and calibration interact.
4. Symmetry-aware matrix-free operator compiler (A/F): rejected because a
   straightforward reconstruction of existing XDiag internals could suffice.
5. Lanczos convergence false-positive witness (B): not built. Ghost roots and
   small-overlap examples risk reducing to a textbook adversarial spectrum.
6. Balanced distributed Hilbert-space layout (A/C): not built. A graph partitioner
   might dominate a hashing baseline without requiring new scientific insight.
7. Finite-temperature spectral reconstruction from noisy imaginary-time data (D):
   not built. High difficulty, but irreducible identifiability makes a fixed
   pass threshold harder to defend than the selected explicit simulators.
8. Fermionic distributed current-operator repair (F): not built. Genuine official
   issue, but compilation/MPI setup could dominate the evidence of difficulty.
9. Sublattice-coding group-design witness (C): not built. A standard group-action
   construction may supply the entire solution.
10. Low-energy block Krylov portfolio (A): not built. Without a very carefully
    tuned resource suite this collapses to choosing one standard algorithm.

Exactly three concepts are built, using modes A, C, and E. Privileged assets,
held-out parameters, checkers, search logs, and previous submissions stay outside
the participant allowlists. Thresholds are frozen before the first tournament.
