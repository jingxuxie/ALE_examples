# Sparse Pauli-channel reconstruction

Recover significant arbitrary-weight Pauli errors and their probabilities from noisy, structured eigenvalue observations of 40–100-qubit channels. Resolve sampling collisions without assuming local support, and estimate probabilities despite large dynamic range and weak nonsparse backgrounds.

Submit one reusable `solver.py`, invoked as `python solver.py INPUT.npz OUTPUT.npz`. Support recovery and probability estimation are assessed separately on hidden channels. Use Python, NumPy, and SciPy; each case allows one CPU thread, 2 GiB address space, and 120 seconds.

The complete observation and submission contract is in `input/FORMAT.md`. `input/example.npz` is an unlabeled format example. Develop in `workspace/`; submit a solver, not a table of example-specific predictions.
