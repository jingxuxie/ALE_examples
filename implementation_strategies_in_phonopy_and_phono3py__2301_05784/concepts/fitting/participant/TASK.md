# Fit harmonic and cubic force constants

Recover second- and third-order interatomic force constants from the supplied
displacement–force snapshots. The data are noisy calculations on periodic
crystals, not forces generated from an exact truncated polynomial.

Deliver `solve.py` into the runner-designated attempt/output directory. The
participant workspace is a read-only starter, not the submission destination.
The solver takes exactly two positional arguments:

```
python solve.py INPUT.npz OUTPUT.npz
```

Write finite float64 `fc2` and `fc3` arrays. The first atom index is compact;
harmonic and cubic supercells can differ. Harmonic cases retain up to 512
atoms, without requiring a 512-atom cubic tensor. `workspace/CONTRACT.md`
specifies all arrays, geometry, units, maps, symmetries, and objectives.

Both orders, unseen real-force predictions, acoustic sum rules, permutation
symmetry, crystal symmetry, and cubic support matter. Scores vary continuously
with error. Zero tensors or a harmonic-only fit do not solve the task.

Do not assume a fixed material, atom ordering, or snapshot count. The starter
is weak unconstrained regression. `input/smoke.npz` is unlabeled and contains
no targets.
