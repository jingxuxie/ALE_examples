# Find a premature-screening witness

Search for one Hamiltonian whose **every third-order virtual-orbital increment is tiny**, yet whose omitted fourth-and-higher-order energy is material. Submit `witness.json` directly in the writable output directory supplied by the runner. No submitted program is executed.

The fixed instance has six electrons: three pairs in three occupied plus seven virtual spatial orbitals. Optimize the 21 real virtual pair hoppings and 21 virtual density interactions. All other coefficients are fixed in `input/target.json`; changing public files does not change the evaluator.

A passing witness simultaneously has:

- All 35 triple increments at most **1 microEh** in absolute value.
- Absolute missing tail beyond third order at least **50 microEh**.
- Tail / largest absolute triple increment at least **100**, using the specified numerical floor.
- Reference determinant weight at least **0.95**, seniority-zero spectral gap at least **0.4 Eh**, and diagonal reference excitation margin at least **0.6 Eh**.
- Real symmetric zero-diagonal virtual matrices, with hopping magnitude at most **0.45 Eh** and density magnitude at most **0.60 Eh**.

This is a bounded, nonuniform **model Hamiltonian testbed**, not a literal ab initio molecule or a disproof of a universal theorem. It tests the precise gate in `input/FORMAT.md`, inspired by arXiv:1807.01328 Eq. (6). The paper itself warns against false convergence from signed increments; its production thresholds are not this benchmark's thresholds.

The participant directory is read-only. Use your supplied writable directory for
the final witness and all scratch files. Construction time is one hour. From the
participant directory, replacing `/path/to/output` with that writable directory:

```sh
python workspace/baseline.py --output /path/to/output/witness.json
python workspace/check.py /path/to/output/witness.json
python workspace/check.py /path/to/output/witness.json --details
```

The baseline is admissible but not a witness. The public checker provides exact-diagonalization diagnostics, not an optimizer. **The task is numerical search, not implementing the supplied formulas.** The bottleneck score in `input/FORMAT.md` rewards progress, but `passed=true` requires every condition. There are no hidden Hamiltonian families. Read `input/FORMAT.md` for the complete model, gate, JSON schema, scoring, and numerical conventions.
