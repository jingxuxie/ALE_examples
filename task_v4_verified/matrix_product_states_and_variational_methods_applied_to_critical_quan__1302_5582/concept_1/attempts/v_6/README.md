# Parity-conserving variational MPS solver

## Submission interface

```sh
python solve.py --request REQUEST.json --output STATE.npz
```

The solver requires only Python, NumPy, and SciPy. It reads the supplied finite-chain
Hamiltonian and emits an uncompressed NPZ containing exactly `A0` through
`A{n_sites-1}`. It does not use stored states, case identifiers, external data,
subprocesses, network access, or multiple numerical threads.

## Method

- Use the supplied padded oscillator operators and a parity-preserving local
  eigenbasis; transform all tensors back before saving.
- Initialize a parity-projected Hartree state, grow its bonds, and perform
  preconditioned single-site DMRG with a reduced two-site initialization sweep.
- Retain the starter's gauge-aligned, energy-tested sweep extrapolation.
- After continuous optimization converges, optimize the **integer allocation of
  even and odd virtual states**. Enrich each neighboring block with its position
  operator, solve the reduced two-block problem, and try transferring one bond
  channel between parity sectors without exceeding the bond cap.
- Relax each proposed allocation in the full physical bases of the two sites.
  Accept it only when its contracted variational energy improves on the unchanged
  state. Long-budget confirmation passes can relax a four-site neighborhood.
- Preserve the best state, check CPU and wall time inside sweeps and local solves,
  and stop early after both continuous and discrete convergence. CPU accounting
  uses user-plus-system resource usage, with a reserve for serialization and exit.

The new production implementation is in `production.py`, `variational.py`, and
`window.py`. The supplied numerical primitives and public contractor remain in
`fast.py`, `optimizer.py`, and `contractor.py`.

## Checks and observed energies

The public contractor recomputes every reported energy and validates each NPZ.
For the three provided examples, the long-budget results are:

| Provided example | Supplied baseline | Submission |
| --- | ---: | ---: |
| `example_symmetric.json` | 27.845578383255 | 27.845578383255 |
| `example_odd.json` | 22.528477943640 | 22.528467662482 |
| `example_nonuniform.json` | 24.337353189147 | 24.337353042963 |

These are finite, cap-compliant variational energies, not continuum estimates or
claims of exact many-body ground energies. No hidden-suite score is available.

Validation scripts are supplied under `experiments/`:

```sh
python experiments/check_exact.py
python experiments/check_reallocation.py
bash experiments/verify.sh
bash experiments/verify_stress.sh
```

The exact check compares both parity sectors against independently assembled
four-site dense Hamiltonians. The reallocation check verifies energy monotonicity,
parity, and consistency of updated environments on six random MPS inputs.
The budget check covers the three public examples and six generated coefficient
profiles at both 6 and 40 CPU seconds, with hard CPU/wall guards and a 2 GiB
address-space limit. The generated checks also include odd local and bond
dimensions and the maximum advertised chain length, local dimension, and bond cap.
Three additional six-second stress cases cover extreme coefficient values and
odd local/bond dimensions. All 21 guarded runs produce valid states within their
CPU, wall, and address-space limits.

`experiments/summary.json` records measured energies, timings, validation results,
and production-source hashes. The three `experiments/verified_*_6.npz` public
example states are retained as concrete validated output samples; the solver never
loads them.
