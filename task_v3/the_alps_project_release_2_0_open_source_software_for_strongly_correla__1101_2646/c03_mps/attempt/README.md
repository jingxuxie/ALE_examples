# Conserved-sector finite-system spectroscopy

Run the required interface with:

```
python solve.py --input INPUT.json --output OUTPUT.json
```

The implementation uses only Python, NumPy, and SciPy. It performs finite-system,
two-site density-matrix renormalization group (DMRG) sweeps with explicit U(1)
charge conservation. All calculations use the supplied finite Hamiltonian,
local cutoff, individual bonds, and site-dependent coefficients. Ladder rungs
are grouped into four-dimensional local spaces without approximating their
interactions. Local eigenproblems use diagonally preconditioned, restarted
Davidson iteration, with ARPACK as a convergence fallback. Local eigensolver
tolerances tighten with the discarded weight rather than over-solving strongly
truncated intermediate states.

Each requested sector is optimized separately. For larger systems, independent
sector calculations run concurrently, using at most three single-threaded CPU
workers. Small systems reuse a charge-shifted ground-state MPS. Bond dimensions
increase adaptively up to 512 for spins and 384 for bosons, subject to the wall
clock budget; singular-value truncation and energy convergence
control stopping. Spin-sector workers compare both antiferromagnetic starting
orientations before increasing the bond dimension, reducing metastability in
easy-axis and field-pinned cases. The default internal time budget is 560 seconds,
leaving headroom beneath the 600-second invocation limit. A partially completed
sweep is discarded if its allotted time expires, preserving a normalized,
canonical state and a consistent energy.

Correlations are evaluated directly in the conserved-sector ground-state MPS.
The measurement implementation shares transfer matrices between requests and
uses charge blocks for diagonal, off-diagonal, and string operators. It retains
the specified string sign, endpoint exclusion, spin-half normalization,
one-body convention, and disconnected-density subtraction.

Optional CLI flags are `--verbose` for sweep diagnostics and `--budget SECONDS`
for experiments. Output diagnostics include sweep energies, maximum bond
dimensions, discarded weights, and elapsed time; the required fields are
`energy`, `gap`, and `correlations`.

Run independent small-system exact-diagonalization regression tests with:

```
python -m unittest -v test_solver
```

`benchmark.py FAMILY LENGTH` generates an inhomogeneous benchmark.
`stress.py FAMILY LENGTH` generates a uniform weak-rung ladder, Heisenberg
spin-one chain, or low-interaction Bose-Hubbard chain. Both write their inputs,
outputs, and diagnostics within this directory.

`python check_symmetry.py` additionally checks spin-inversion invariance on a
32-site easy-axis chain, including reversed longitudinal fields and sectors.
