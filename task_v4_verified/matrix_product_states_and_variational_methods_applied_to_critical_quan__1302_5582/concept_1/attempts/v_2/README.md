# Finite-chain phi4 MPS optimizer

This directory is the submission. The entry point is `solve.py`:

```sh
python solve.py --request REQUEST.json --output STATE.npz
```

Runtime dependencies are Python, NumPy, and SciPy. Only `solve.py`,
`optimizer.py`, and `contractor.py` are needed to run the submission. The solver
does not read experiment files, launch subprocesses, use external services, or
reuse states between requests. It writes an uncompressed NPZ containing only
`A0`, ..., `A{n_sites-1}`.

## Optimization

- Uses the exact padded-space local operators from the supplied contractor.
- Diagonalizes each on-site Hamiltonian internally, without reducing the
  physical dimension, and transforms every output tensor back to the requested
  oscillator basis.
- Initializes from self-consistent product states. For unconstrained requests,
  a two-state dynamic program finds favorable sign domains across interfaces
  and weak links. Unequal initial branch weights allow spontaneous symmetry
  breaking when it improves the bond-capped unrestricted variational energy.
- Enforces requested parity through explicit binary bond charges, including
  charge-block SVDs and block-sparse effective Hamiltonian applications. No
  final projection doubles the bond dimension.
- Uses three two-site sweeps, growing to the requested bond cap, followed by
  converged one-site variational sweeps. The latter remove energy errors caused
  by repeated two-site truncation.
- Solves local eigenproblems with a diagonally preconditioned, restarted
  Davidson method and cached projected Hamiltonians.
- Checks CPU and wall deadlines during local eigensolves and between tensor
  updates. Every interruption point leaves a valid MPS. The CLI CPU deadline
  includes interpreter/import time and reserves time for serialization/exit.

## Checks

`VALIDATION.md` summarizes the checks. `experiments/` contains reproducible
numerical checks and their logs; these are not solver inputs. `mps.py` is the
unchanged supplied tensor engine, retained only for baseline comparisons.

From this directory:

```sh
OPENBLAS_NUM_THREADS=1 python experiments/exact_check.py
bash experiments/cold_check.sh 6
bash experiments/cold_check.sh 40
OPENBLAS_NUM_THREADS=1 python experiments/sweep_check.py
```

The cold-start check uses the shell's CPU and 2 GiB address-space limits. It
launches independent solver processes, validates their files with the public
contractor, and records CPU time, wall time, and peak resident memory.

The official hidden cases, references, and evaluator are not participant assets;
no official score or target-gate result is claimed.
