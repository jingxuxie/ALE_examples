# Finite-field MPS under a clock

## Mission
Improve the supplied runnable, limited-sweep optimizer for finite open-chain lattice
phi4 Hamiltonians. Return low-energy matrix product states within the requested
bond cap, including the requested parity sector when specified. The hidden suite
covers symmetric, finite-size crossover, deep double-well, and inhomogeneous chains.
This is an optimizer-improvement task, not a continuum-limit or gap-prediction task.

## Assets
`workspace/` contains a starter solver, tensor routines, and the public energy
contractor. `baseline/` is the frozen weak solver. `input/` contains the precise
contract, examples, and public scoring specification. Only these participant
assets are available read-only during an isolated attempt; copy starter code into
your submission/output directory before changing it.

## Interface
Submit a self-contained directory with `solve.py`. Each independent invocation is
`python solve.py --request REQUEST.json --output STATE.npz`. Submit finite open
MPS tensors, not energy claims. See `input/CONTRACT.md` for array conventions and
the exact projected Hamiltonian.

## Objective
The evaluator recomputes energies. A frozen score rewards logarithmic energy
improvement over the baseline at two compute budgets, the worst family, and
quality-adjusted runtime. The target is score >= 80, core >= 0.80, worst-family
>= 0.70, every long-budget quality >= 0.55, and all outputs valid. The reference
energies are attainable, bond-capped variational energies, not asserted exact
ground energies. See `input/scoring.json`.

## Resources
Eight hidden chains; 6-second and 40-second CPU budgets per chain in independent
cold-start processes, with 30/120-second wall guards. One execution thread, 2 GiB address space,
no GPU, network, subprocesses, or cross-request state. Python, NumPy, and SciPy
are available; no tensor-network package is required. BLAS/OMP threads are one.
Typical full evaluation is much shorter than the 1200-second wall-budget ceiling.
