# Transport through finite Wannier devices

Extend the supplied bulk interpolation code into a sparse, open-device transport solver. Inputs contain complete long-range Si or InAs Wannier Hamiltonians, finite crystal cells, electrostatic gates, and two or three periodic leads. Return causal lead selfenergies, channel counts, lead-to-lead transmission, transmission eigenvalues, partition noise, and the Landauer–Büttiker conductance matrix.

Implement `attempt/solve.py` with this interface:

```text
python attempt/solve.py --input CASE.npz --output RESULT.npz
```

The complete conventions and array shapes are in `workspace/SCHEMA.md`. `input/example.npz` is the single unlabeled smoke input. The existing `workspace/solve.py` only evaluates bulk bands; those are not transport answers. Copy the starting workspace into `attempt/`, then extend it. NumPy and SciPy are available; no transport library is provided.

Retain every supplied hopping and use the specified lead interfaces and ordering. Inter-layer hopping can be singular. Do not assume invertible transfer matrices, nearest-neighbor primitive cells, two contacts, or that a total transmission determines its channel spectrum. Scored devices have roughly 7,000–12,000 orbitals; each process has a 90-second wall-time limit and a 1,024 MiB address-space limit, with single-threaded BLAS. Avoid dense device inverses.

These are ideal finite cuts of actual bulk Wannier models, not experimentally calibrated surface devices. Scores measure continuous numerical error reduction relative to the existing bulk-only capability, balanced across materials and contact geometries. Write only your implementation and requested output; do not access author-only references or evaluation metadata.
