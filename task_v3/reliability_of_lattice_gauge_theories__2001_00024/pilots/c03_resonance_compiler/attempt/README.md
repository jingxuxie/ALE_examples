# Local protection compiler submission

The entry point is `solver.solve(case)`. It returns the complete per-instance
sector/penalty certificate and independently optimized analog and digital
schedules. The module also accepts one JSON case on standard input and writes
one JSON response on standard output.

## Scientific implementation

The compiler decomposes every operator into input-dependent flip paths and
groups paths by their exact output flip set. It sums amplitudes coherently
within each channel before testing reachability. Only the local link bits needed
by a group and its neighboring gauge constraints are enumerated. U1 assignments
with any fixed adjacent occupied links are excluded, including pairs outside
the directly affected gauge sites. All remaining local assignments extend to
the target ring. Z2 matter occupations are reconstructed using the supplied
site-dependent targets, and sector and pseudogenerator transfers are computed
separately. Translations reuse compilation results when their local target
patterns agree.

The optimizer pools distinct penalty rows modulo overall sign and uses the
protocol's uncertainty corrections exactly. Digital margins are reduced modulo
the kick period, rather than optimized as unwrapped analog gaps. Integer DAC
limits are enforced throughout. Sign-symmetric variables have reduced search
domains only when invariance of the entire pooled constraint set is verified.

`optimizer.cpp` implements single-threaded coordinate searches and bounded-frontier
dynamic programming on cyclic local constraints, with randomized restarts and
full-domain polishing. A min-margin hinge objective guides the search; the
reported candidate is always selected by the actual min/mean robustness score.
Control optimization is heuristic, not a claim of global optimality. The
certificate computation is exact up to the specified cancellation tolerance.

## Files and runtime

- `solver.py`: callable entry point, local algebra, and NumPy fallback optimizer.
- `optimizer.so`: prebuilt Linux x86-64 search library; no compilation is needed
  for the supplied environment.
- `optimizer.cpp`: complete source for the library.
- `validate.py`: independent full-state tests on small rings and screening runs.
- `test_optimizer.py`: exhaustive small-DAC-grid optimizer checks.

The solver budgets approximately 52 seconds, including local compilation, to
leave room under the 60-second process limit for imports and JSON handling.
There are additional deadline checks inside the native search. If the native
library cannot be loaded, a time-bounded NumPy optimizer supplies valid controls.

To rebuild the native library:

```sh
g++ -O3 -std=c++17 -fPIC -shared optimizer.cpp -o optimizer.so
```

## Local validation

From this submission directory:

```sh
OPENBLAS_NUM_THREADS=1 python validate.py \
  --input ../participant/input/screening --compiler --seconds 3
OPENBLAS_NUM_THREADS=1 python test_optimizer.py
python solver.py < ../participant/input/screening/screening_u1_local_00.json
```

Validation includes 686 channel instances compared with independent full-target
enumeration on small rings, including randomized operators, complex amplitudes,
periodic boundaries, exact cancellations, and mixed Z2 targets. All matched.
The optimizer also matched exhaustive global optima on 30 small synthetic DAC
grids. All nine supplied screening cases were exercised, with valid bounded
controls and finite margins. A synthetic 160-site correlated case completed
`solve` in approximately 52 seconds and serialized to less than 210 kB, well below the
32 MiB response limit. These are local checks, not private evaluator scores.
