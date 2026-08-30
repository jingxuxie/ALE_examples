# Matched normal states across distinct phonon spectra

Find two anisotropic electron–phonon kernels with identical complete normal-state mass renormalization and identical static pairing matrices, but a critical-temperature ratio of at least **1.09 in every supplied spectral scenario and refinement**. The same pair must work throughout; optimizing only one spectrum is insufficient.

## Assets and interface

- `input/reference.npz` is the fixed feasible constraint instance; `input/config.json` fixes all bounds, tolerances, spectral scenarios, refinements, and the target.
- `input/FORMAT.md` supplies every equation and the artifact format. `workspace/physics.py` is a working solver and artifact validator; `workspace/check.py` is the public check. Implement search, not an equation solver.
- `workspace/solve.py` is a runnable starting point; `baseline/solve.py` emits the same feasible reference twice.
- Produce `witness.npz` with only a real numeric array `kernels` of shape `(2,3,8,8)`. Evaluation consumes this artifact, never submitted code.

## Constraints

Both kernels independently match all supplied per-mode labeled weighted row sums, mode diagonals, and the full static aggregate. Each mode matrix is symmetric and within the fixed entry bounds. Comparisons use published absolute tolerances. Patch and mode labels are fixed; do not change the input. Mode labels do not imply frequency ordering across scenarios.

## Scoring and success

The score is the minimum ordered high/low critical-temperature ratio across all four spectral scenarios and all prescribed Matsubara grids. Choose the kernel ordering once from the nominal fine grid and retain it everywhere. A repeated reference scores `1.0`.

`admissible` means the matrix constraints pass. `valid` additionally requires score at least `1.09`, refinement convergence, and the independent signed-frequency and regular-row controls. The evaluator reports a reason, `core_score`, `worst_family_score`, timing/resources, and a saved audit. Both score summaries equal the minimum ratio just defined; admissibility alone is not success. There is no absolute temperature-difference target.

Run `python workspace/check.py witness.npz --output public_check.json` from this directory. The public check reports constraints and physics; the evaluator adds independent audits. The supplied spectra are distinct positive-phonon stress scenarios, not small isotope uncertainties or a claimed material trajectory. This is a clean, constant-DOS, Fermi-surface-restricted model with zero Coulomb pseudopotential, not a claim of synthesizable materials.
