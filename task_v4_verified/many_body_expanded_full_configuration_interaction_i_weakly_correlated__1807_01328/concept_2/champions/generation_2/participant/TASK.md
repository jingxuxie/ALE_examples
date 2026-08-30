# Find a persistent premature-screening witness

Produce one pair-conserving model Hamiltonian whose premature-screening counterexample persists in a specified perturbation assay. Submit **`witness.json` directly in your writable working-directory root**, not in `output/` or inside this read-only participant packet. Only static JSON is evaluated; no submitted code is executed.

There are three electron pairs, three occupied orbitals, seven virtual orbitals, and 42 adjustable real virtual hopping/density coefficients. All remaining coefficients and all nominal thresholds are fixed.

The nominal Hamiltonian must have:

- Every triple increment at most **1 microEh** in absolute value.
- Net omitted fourth-and-higher-order tail at least **50 microEh** and tail/largest-triple ratio at least **100**.
- Reference weight at least **0.95**, paired-sector gap at least **0.4 Eh**, and diagonal reference margin at least **0.6 Eh**.

In addition, **at least 122 of 128 frozen hidden perturbations must satisfy those same conditions**. Each of the 42 coefficients is independently sampled uniformly within 0.001 Eh of its nominal value, truncated to its allowed coefficient interval; symmetry is restored exactly. The complete distribution and acceptance rules are public in `input/FORMAT.md`. Hidden random draws are private and fixed, not regenerated between evaluations.

This is a finite, machine-checkable robustness assay, **not universal robustness or a 95% population guarantee**. The Hamiltonian is an effective electronic model, not a literal ab initio molecule. The supplied gate is inspired by arXiv:1807.01328 Eq. (6); no universal theorem is attributed to that paper.

The original zero-coefficient baseline is in `input/baseline_witness.json`. It is physically admissible but does not solve the task. `workspace/baseline.py` writes it to a requested writable path. `workspace/check.py` evaluates independent public training draws; its result is diagnostic, not the hidden score. Both can be invoked by absolute path from your writable working directory. NumPy and SciPy are the only nonstandard dependencies. Read `input/FORMAT.md` for the mathematical definition and exact JSON schema.
