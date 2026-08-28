# Sparse Pauli-channel solver

Run the standalone submission with:

```
python solver.py INPUT.npz OUTPUT.npz
```

Only `solver.py` is required. Its dependencies are Python, NumPy, and SciPy.
It sets numerical libraries to one thread before importing them.

## Reconstruction

The solver transforms the eigenvalue observations into signed hash-bin
mixtures using normalized Walsh-Hadamard transforms. It combines:

- Direct singleton and dominant-term decoding with independent validation.
- Reliability-ordered binary syndrome decoding using hash and offset checks.
- Pair and multi-group fusion, reserving masks for validation.
- Doubleton XOR recovery and physical probability bounds to resolve collisions.
- Support refinement and conservative restarts to undo incorrect peeling.
- Joint noise-weighted nonnegative probability fitting with a unit-mass bound.
- Residual-based weighting of uncertain bins for weak nonsparse backgrounds.

The probability model explicitly includes the possible diffuse remainder and
removes the known zero-character contribution. Recovery does not restrict
Pauli weight or enumerate the exponentially large Pauli space.

The solver limits its candidate pool and checks elapsed time during decoding,
leaving time for final probability fitting and output serialization.

## Development checks

`test_solver.py` generates and scores independent synthetic channels.
`stress_tests.py` exercises 40--100 qubits, up to 512 significant terms,
commuting hash matrices, equal-weight collisions, large dynamic range,
heterogeneous noise, weak backgrounds, and low-weight supports.

`validation_tests.py` checks the output contract, empty supports, zero output
capacity, identity-free channels, and execution with 2 GiB address space,
64 file descriptors, and a 120-second CPU/wall-time allowance. The public
unlabeled example is also used only for format and execution checks.

These development files are not runtime dependencies of `solver.py`.
