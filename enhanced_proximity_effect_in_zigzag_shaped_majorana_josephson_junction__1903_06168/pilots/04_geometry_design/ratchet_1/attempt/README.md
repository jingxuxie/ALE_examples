# Periodic contact optimizer

Run the self-contained submission with Python, NumPy, SciPy, and threadpoolctl:

```sh
python /absolute/attempt/solve.py --input /absolute/request.json --output /absolute/result.json
```

The optimizer uses the exact supplied operating points and the unmodified full-scale physical model. It screens smooth reflected contact profiles, locally optimizes their parameters, and refines individual reflected boundary pairs using eigenstate derivatives. Every candidate passes the fabrication validator. Reflection-sector determinants check the class-D phase at both invariant momenta for all operating points. Increasingly dense momentum scans select the result, with a final 51-point scan limited by the remaining runtime.

The implementation uses at most two single-threaded workers, respects the request's wall-time budget with a safety margin, and atomically checkpoints complete geometry-only JSON results. The supplied baseline is the initial fallback. Progress and numerical diagnostics go to standard error, never into the result JSON.

For a full 51-momentum, eight-state diagnostic using the exact Hamiltonian and authoritative Pfaffian invariant:

```sh
python /absolute/attempt/validate.py --input /absolute/request.json --geometry /absolute/result.json --output /absolute/attempt/validation.json --momenta 51 --topology
```

Omit `--geometry` to evaluate the request's baseline. The optional `SOLVE_SECONDS` environment variable caps optimizer time for development; the default uses the documented request budget.

The diagnostic uses a faster sparse ordering, checks eigenvector residuals, and cross-checks both endpoints and the minimum against the unmodified authoritative eigensolver.
