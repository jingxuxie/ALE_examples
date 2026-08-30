# Accurate energy, impossible orbital population?

Find a counterexample to this **task-supplied screening heuristic**: a stable
canonical Hartree–Fock reference, a well-conditioned ground-connected CCSD root,
nearly exact ground energy, and high exact-state fidelity are sufficient to trust
its unrelaxed lambda one-particle density as a physical orbital-population model.

Submit a small real Hermitian one-/two-body fermion Hamiltonian whose verified
CCSD lambda density assigns some normalized real orbital a population at least
**0.02 below zero or above one**, while passing every reference, stationarity,
accuracy, conditioning, and ground-connection constraint. The fixed system has
three fermions in six spin-orbitals. The energy-error tolerance is **0.0001** in
units of the canonical occupied–virtual gap.

The scientific seed is Rubin and DePrince, arXiv:2106.06850, particularly its
unrelaxed CCSD RDM construction. The paper does **not** assert the heuristic
being challenged. This is a constrained Hamiltonian witness search, not a request
to derive or implement those equations. Arbitrary amplitudes are not witnesses.

Read `workspace/API.md` for the full mathematical contract and artifact format.
`workspace/oracle.py` supplies a small determinant-space numerical oracle;
`workspace/constraints.json` contains all fixed thresholds. Run the reproducible
starter with `bash baseline/run.sh --output submission.json`.

Return **one JSON artifact**, normally `submission.json`, not executable code.
The evaluator independently reconstructs the Hamiltonian, checks the submitted
stationary root, follows the prescribed coupling path, solves lambda, and computes
exact reference diagnostics. There are no hidden physical constraints. Improving
the search strategy is the work; the starter is intentionally only random search.
