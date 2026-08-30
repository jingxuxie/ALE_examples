# An adaptively probed, Hermiticity-quiet CCSD density counterexample

Find a Hamiltonian family falsifying this **task-supplied screening heuristic**:
a stable canonical HF reference, an accurate ground-connected CCSD root, and a
nearly Hermitian lambda density suffice to trust its real-orbital populations,
provided the same favorable screens persist under small integral perturbations.

Submit one real one-/two-body Hamiltonian for three fermions in six spin-orbitals.
The base Hamiltonian **and all 242 public finite perturbations** must retain
a lambda-density real-orbital population at least **0.02 outside [0,1]**, while
passing every original reference, stationarity, energy, fidelity, conditioning,
and ground-connection constraint. At every point, energy error must be at most
**1e-4** and `DAD = ||gamma-gamma.T||_F/sqrt(3)` at most **0.001**.

Every perturbation has radius **0.001 in pair-matrix Frobenius norm**. The probes
include both signs of 120 orthonormal symmetric coordinate axes and both signs
of the base signed CCSD-minus-FCI energy-error gradient, normalized in that basis.
This public adaptive rule checks actual neighboring roots, not a derivative proxy.
Every perturbed matrix must stay in the allowed domain; there is no clipping.
The score is the **worst population violation across all 243 labeled points**.
This finite-probe criterion makes no claim about an entire continuous norm ball.

Assets: `workspace/API.md` specifies the complete contract;
`workspace/constraints.json` and `workspace/stencil.json` fix all thresholds and
points. The numerical oracle, `api.robust_screen`, and `workspace/adaptive.py`
support search and verification. `baseline/run.sh` supplies random search.

Interface: return one `submission.json` containing the base pair matrix and its
stationary CCSD amplitudes, in the unchanged documented format. The evaluator
recomputes the gradient, every neighboring root, and all 243 continuation certificates;
it never executes submitted code. Its wall limit is **900 seconds**. Python,
NumPy, and SciPy are sufficient; use single-threaded BLAS for these small matrices.

The scientific seeds are arXiv:2106.06850 (unrelaxed CCSD RDMs) and
arXiv:2503.20006v2 (the density asymmetry diagnostic). Neither paper asserts this
task's combined heuristic, robustness criterion, or numerical thresholds.
