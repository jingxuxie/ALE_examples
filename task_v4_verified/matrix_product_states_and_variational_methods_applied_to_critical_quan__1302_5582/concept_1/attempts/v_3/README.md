# Budgeted finite-chain phi4 MPS optimizer

This directory is the submission. The entry point writes the requested MPS,
not an energy estimate:

```sh
python solve.py --request REQUEST.json --output STATE.npz
```

The solver uses only the request, its bundled implementation, NumPy, SciPy, and
the installed CPU BLAS/LAPACK libraries. It does not launch processes, use a
network, or read checkpoints. Requests are independent, with no cross-request
state; numerical stopping depends on the current invocation's clocks.

## Algorithm

- Construct the exact padded-oscillator operators specified by the contract.
  Diagonalize onsite terms internally and transform all output tensors back to
  the requested oscillator bases.
- Start from self-consistent Hartree branches, including a domain-sensitive
  branch for spatially varying fields. Enforce requested global parity through
  explicit virtual charges. Zero-field unrestricted ground-state requests use
  the even sector when the onsite spectra have the usual parity ordering;
  cutoff-induced local parity inversions retain unrestricted optimization.
- Grow the bond spaces using charge-aware one-site subspace expansion. A few
  targeted two-site updates correct parity allocation near the boundaries.
- Once the requested bond space is established, use inexpensive charge-aware
  QR center moves instead of repeated enlarged SVDs. No intermediate bond in
  the production optimizer exceeds the requested cap.
- Solve local eigenproblems with matrix-free, preconditioned Davidson updates.
  Environment eigensystems are cached. A bundled C helper performs the numerical
  inner loop and directly contracts the four allowed parity blocks.
- Use short local solves during sweeps and more accurate convergence
  confirmation. Require three small sweep-energy changes, rather than stopping
  at the first apparent plateau.
- Reserve CPU and wall time for output. Build the uncompressed NPZ in memory,
  write it in one file operation, and exit after the file has been closed.

## Native helper

`local_solver.so` is supplied prebuilt for the provided Linux x86-64 environment.
No compiler is invoked at solver runtime. Its source is `local_solver.c`; to
rebuild manually in a compatible development environment:

```sh
gcc -O3 -fPIC -shared local_solver.c -o local_solver.new.so -lblas -llapack -lm
mv local_solver.new.so local_solver.so
```

If the helper cannot be loaded, the solver retains a NumPy/SciPy fallback. The
fallback preserves the interface and deadlines but is slower.

## Verification

The original Hamiltonian construction and public validation/measurement logic
remain in `contractor.py`. Its serialization helper only changes the buffering
strategy, not the NPZ format.

```sh
python experiments/checks.py
python experiments/parity_checks.py
python contractor.py --request example_request.json --state example_state.npz
```

`experiments/checks.py` compares local solves and complete small-chain MPS
energies with dense diagonalization. `experiments/parity_checks.py` checks
shuffled charge labels, odd physical dimensions, unequal charge populations,
and boundary bonds. `experiments/cold_runner.py` is a development-only launcher
that measures independent CLI processes under CPU, wall, memory, and file-size
limits; it is never imported by the solver.

`RESULTS.md` summarizes the measured public and self-generated tests. The sample
state is a public-example output, not an optimizer checkpoint; `solve.py` never
reads it. Hidden cases and their official references are unavailable, so no
hidden-suite score is claimed.
