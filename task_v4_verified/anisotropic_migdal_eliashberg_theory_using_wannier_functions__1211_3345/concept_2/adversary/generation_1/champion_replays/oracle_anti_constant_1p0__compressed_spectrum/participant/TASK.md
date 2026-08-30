# Matched normal state, different superconducting transitions

Find two anisotropic electron–phonon kernels whose linearized Migdal–Eliashberg critical temperatures differ despite identical complete normal-state mass renormalization and identical static pairing matrices.

## Assets and interface

- `input/reference.npz` is the fixed feasible constraint instance; `input/config.json` fixes bounds, tolerances, temperature families, and the target.
- `input/FORMAT.md` supplies all equations and the artifact format.
- `workspace/physics.py` supplies the working physics solver and artifact validation. `workspace/check.py` supplies the public check. Implement search, not another equation solver.
- `workspace/solve.py` is a runnable starting point. `baseline/solve.py` emits the same feasible reference kernel twice.
- Produce `witness.npz` containing only a real numeric array named `kernels`, shape `(2, 3, 8, 8)`. No candidate program is executed during evaluation.

## Constraints

Both kernels must independently match the supplied per-mode labeled weighted row sums, mode diagonals, and full static aggregate. Every mode matrix must be symmetric and within the fixed entry bounds. All comparisons use the published absolute tolerances. Patch and phonon labels are fixed. Do not modify the inputs.

## Scoring and success

The score is the worst ordered high/low critical-temperature ratio over the published spectral families and Matsubara refinements. The high/low ordering is chosen once from the nominal fine-grid temperatures. A repeated reference has score `1.0`.

`admissible` means the artifact satisfies the matrix constraints. `valid` additionally requires the configured target ratio, converged transitions, and the independent signed-frequency and regular-row controls. Admissibility alone is not success. The evaluator saves an audit JSON. No absolute temperature-difference target is imposed.

Run `python workspace/check.py witness.npz --output public_check.json` from this directory. The public check reports constraints and physics; the evaluator additionally runs independent audits. This is a clean, constant-DOS, Fermi-surface-restricted model with zero Coulomb pseudopotential, not a claim of synthesizable materials.
