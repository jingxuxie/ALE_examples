# Budget-aware finite-chain phi4 MPS solver

Run the self-contained submission with:

```sh
python solve.py --request REQUEST.json --output STATE.npz
```

The solver needs only Python, NumPy, and SciPy. It writes the requested
uncompressed NPZ containing `A0` through `A{n_sites-1}`. It does not read
checkpoints, launch subprocesses, or use external data. The implementation
uses one numerical thread and observes both CPU and wall-clock deadlines.

## Optimization

- The supplied padded-oscillator Hamiltonian is used unchanged. Physical basis
  changes retain the entire requested local Hilbert space and are undone before
  output.
- Mean-field branches, including a spatial domain candidate, are combined by a
  small generalized variational eigenproblem instead of fixed mixture weights.
- Fixed global parity is represented by explicit bond charges. Unrestricted
  zero-field cases use even parity only after checking for finite-basis local
  parity reversals.
- Single-site Davidson updates use tensor-factorized Hamiltonian actions and
  virtual-block energy eigenbases. Position-operator subspace expansion grows
  bonds cheaply; a reduced two-site sweep repairs their allocation.
- Unrestricted states use an exactly equivalent mean-centered Hamiltonian and
  local eigenbasis. Parity-preserving QR factorizations move the orthogonality
  center without unnecessary singular-value decompositions.
- Gauge-aligned extrapolations are accepted only after contracting their energy.
  Converged parity states can undergo additional bond-charge allocation checks.
  An in-memory best-state checkpoint protects against truncation regressions
  and interrupted refinement sweeps.

## Validation

`experiments/checks.py` compares factorized contractions with the original
contractions and compares optimized small systems against full exact
diagonalization. It includes even and odd sectors, odd physical dimensions,
external fields, and a finite-basis example whose unrestricted ground state
has odd parity. All checks pass to double-precision accuracy.

`experiments/final_validation.txt` records independent cold-start CLI runs at
6- and 40-second CPU budgets, with a 2 GiB virtual-memory limit. Each output is
reloaded and measured using the supplied contractor. The cases include the
three public examples and additional generated 64-site, odd-dimension,
odd-bond-cap, and maximal-field requests.

The retained sample state is `experiments/public/symmetric40.npz`, with its
request at `experiments/requests/symmetric40.json`. Recheck it with:

```sh
python contractor.py --request experiments/requests/symmetric40.json \
    --state experiments/public/symmetric40.npz
```

Only provided public assets and locally generated tests were used. No hidden
suite or evaluator was available, so no hidden score is claimed.
