# Joint fermionic representation optimizer

Run the self-contained submission with:

```sh
python3 solver.py REQUEST.json RESPONSE.json
```

Runtime files are `solver.py`, `search.py`, `optimize.py`, `native.py`, and
`polish.so`. Only the supplied system Python, NumPy, SciPy, and standard native
runtime libraries are required. No training data, external files, network
access, subprocesses, runtime compilation, or worker threads are used.

## Method

1. Construct orbital spectral candidates and identity/Gram-eigenvector auxiliary
   candidates, retaining the lowest exact-cost representation as a fallback.
2. Optimize both orthogonal matrices jointly using Cayley-coordinate L-BFGS
   and a decreasing smooth approximation to the absolute-value objective.
3. Explore several initial candidates and retain distinct low-cost basins.
4. Polish with native Givens rotations. Auxiliary plane searches minimize the
   exact piecewise-trigonometric objective; orbital searches evaluate its zero
   crossings and refine promising intervals.
5. Try additional smoothing schedules, keep only improvements measured using
   the exact specified cost, and apply a final polar orthogonalization.

No Hamiltonian entries or factors are removed or approximated in the output.
The response contains only the two orthogonal transformations for each case.
The smoothing is confined to the optimization procedure, not the represented
Hamiltonian or the final cost.

## Resource control

All numerical-library thread counts are set to one before importing NumPy or
SciPy. Both Python optimization and native polishing check wall-clock deadlines.
The solver reserves 10% of the requested total per-case allowance and caps its
overall working budget at 173 seconds, including interpreter import time after
the script starts. For eighteen ten-second cases, the working budget is 162
seconds. Candidate selection always leaves a valid fallback.

`validate_limits.py` can run the solver under a 2 GiB address-space limit, a
175-second CPU limit, and one-CPU affinity:

```sh
python3 validate_limits.py REQUEST.json RESPONSE.json RUNTIME_REPORT.json
```

## Public validation

The supplied scorer reports the following on all twelve public instances:

| Metric | Reduction |
| --- | ---: |
| Aggregate geometric-mean cost | 45.54% |
| Bond-charge family | 21.43% |
| Overlapping-cluster family | 33.67% |
| Multiscale family | 69.01% |

All transformations pass the supplied validator; the maximum measured
orthogonality residual is below 3.4e-15 (see `validity_report.json`). The constrained run used
107.85 seconds wall time, 19.08 seconds CPU time, 60,692 KiB peak resident memory,
and one thread. Timings depend on CPU scheduling; the solver checks wall time
throughout. Machine-readable results are in `public_score.json` and
`public_runtime.json`.

An additional eighteen-case gauge-robustness check applies fresh random
orthogonal orbital and auxiliary transformations to public Hamiltonians. It
passes all validity checks with 43.55% aggregate reduction and 21.27%
worst-family reduction. Under the same resource limits it uses 158.35 seconds
wall time, 34.51 seconds CPU time, 61,140 KiB peak resident memory, and one
thread. Results are in `gauge_score.json` and `gauge_runtime.json`. This is a
public-data robustness check, not a measurement on hidden instances.

The required initial access check is recorded in `isolation_audit.json`.

## Rebuilding the optional native component

The precompiled library is included, so rebuilding is unnecessary for inference.
Its source is `polish.cpp`. The development build command is:

```sh
g++ -O3 -std=c++17 -fPIC -shared polish.cpp -o polish.so
```
