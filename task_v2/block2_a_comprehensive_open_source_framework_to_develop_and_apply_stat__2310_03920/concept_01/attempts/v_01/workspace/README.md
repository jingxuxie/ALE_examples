# Repaired transport workspace

`../run.sh CASE.json RUN_DIRECTORY [production|baseline|refined]` is the public entry point. Set `ALE_ASSETS` to the supplied read-only asset directory. It initializes the provided runtime and writes the required trajectory and statistics without looking at the case identifier or family.

- `solve.py`: physical-dimension/memory dispatch, profile policies, output contract.
- `sparse_solver.py`: independently assembled sector-restricted sparse Hamiltonians, ground eigensolver, exponential-action propagation, operator continuity check.
- `tensor_solver.py`: spatial-electron/boson local matrices, symmetry-preserving MPOs, DMRG and TDVP, graph ordering, preparation variance option.
- `mode_solver.py`: two-state electronic modes for number/parity symmetries; exact fermionic signs and separate boson degrees of freedom.
- `legacy/`: copied legacy fixture with independent environment switches for clock and interaction repairs. It is not used by the submitted production solver.
- `*experiments.py`: development, ablation and size-case construction and execution. Historical candidates are best replayed with their saved configuration, not a changed default profile.
- `package_evidence.py`, `verify.py`, `report.py`: linked tables/figures, dense spectral verification, quantitative claims and report.

Each successful run has a `replay.sh` taking a new output directory. It freezes its configuration and physical tensor ordering through `ALE_SETTINGS`; this environment variable is an optional research override, not required by the public contract. All scientific options actually used are in `stats.json`. Run `ALE_ASSETS=... bash ../build_evidence.sh` to regenerate the evidence from the saved outputs.

The oscillator cutoff is part of the input Hamiltonian, never an accuracy knob. Ground energy is measured in the actual prepared state. Current and pair source are distinct regional commutators. No reporting-only normalization alters the norm column. The final report distinguishes cross-method accuracy checks, finite-resolution continuity, finite-bond comparisons, failed resource pilots and unsupported steady-state extrapolations.
