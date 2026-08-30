# Near-Hermitian density, impossible orbital population?

Find a counterexample to this **task-supplied screening heuristic**: a stable
canonical Hartree–Fock reference, a well-conditioned ground-connected CCSD root,
nearly exact ground energy, high exact-state fidelity, and a nearly Hermitian
unrelaxed lambda density are sufficient to trust its real-orbital populations.

Submit a small real Hermitian one-/two-body fermion Hamiltonian whose verified
CCSD lambda density assigns some normalized real orbital a population at least
**0.02 below zero or above one**, while passing every reference, stationarity,
accuracy, conditioning, density-asymmetry, and ground-connection constraint. The fixed system has
three fermions in six spin-orbitals. The energy-error tolerance is **0.0001** in
units of the canonical occupied–virtual gap.

The added density screen is **DAD <= 0.001**, where
`DAD = ||gamma - gamma.T||_F / sqrt(3)` is computed from the full unsymmetrized
lambda density. A large asymmetry is therefore not an acceptable counterexample.

The scientific seed is Rubin and DePrince, arXiv:2106.06850, particularly its
unrelaxed CCSD RDM construction. The stronger density-asymmetry screen is motivated
by Weflen et al., arXiv:2503.20006v2. Neither paper asserts this task's screening
heuristic as a theorem or supplies its thresholds. This is a constrained Hamiltonian witness search, not a request
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
