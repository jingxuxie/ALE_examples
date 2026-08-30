# Calibration-matched counterexample

The final submission is `witness.json`. The supplied deterministic checker
accepts it; its output is saved in `validation.json`.

Run from the participant directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python workspace/check.py ../attempts/v_3/witness.json
```

Every layer has total nonidentity count 60, hence infidelity exactly 0.02.
The single-qubit and CNOT family marginal deviations from the baseline are
both exactly zero. Their unweighted inverse-pair overlaps are respectively
28800 and 1920, giving weighted overlap 32640.

## Search method

The search parameterizes all row-sum and family-marginal equalities using a
linear nullspace. Within that nullspace, the two remaining family overlap
constraints are separate quadratic equalities. A compiled evaluator computes
the exact 129-point polarization curve and an adjoint derivative of its fitted
bias. Constrained continuous optimization locates candidate allocations.

An integral transportation linear program rounds the allocations while
preserving all linear equalities. Pairs of integer transportation moves repair
any remaining overlap discrepancies exactly and improve the fitted bias. Each
saved candidate passes the original integer constraint checker, and the final
witness is independently evaluated by the public checker.

The working search sources are `kernel.cpp`, `search.py`, and `integer.py`.
To repeat the successful search seed from this output directory:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 TMPDIR="$PWD"
g++ -O3 -std=c++17 -shared -fPIC kernel.cpp -o kernel.so
python -c 'import search; search.optimize(13)'
python integer.py
python ../../participant/workspace/check.py witness.json
```

The JSON witness itself requires no compilation or search to check.
