# Symmetry-complete orbital response

Extend the supplied atomic Hamiltonian workflow into a symmetry-consistent
operator and response pipeline. Preserve the complete real-space model, restore
both its Hamiltonian and position connection under the supplied magnetic space
group, and compute the requested Berry traces and optical transition kernels
before and after repair. Band energies alone are insufficient.

Copy `workspace/` to your writable attempt directory. Implement
`python attempt/solve.py --input CASE --output RESULT.npz`.
The precise array, gauge, and observable contract is in `workspace/SCHEMA.md`.
One unlabeled full-material smoke case is supplied under `input/smoke/`;
`workspace/smoke_check.py` checks invariants only.

Evaluation includes unseen materials, orbital conventions, and Cartesian frames.
Operator repair and the original-model response receive independent credit.
Do not rely on network access, private files, or an installed modern Wannier
response package. The supplied implementation has Hamiltonian-only capability;
you may modify or replace it.
