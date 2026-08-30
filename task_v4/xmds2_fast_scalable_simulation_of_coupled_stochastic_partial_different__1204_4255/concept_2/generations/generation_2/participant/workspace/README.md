# Local interface

From the generation root:

```
/usr/bin/python3 -B participant/baseline/search.py --output attempts/baseline.json
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --guards --family
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --quick --family
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json
/usr/bin/python3 -B evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json
```

In a participant-only checkout, select a writable output location instead of `attempts/`; the first four commands require no evaluator files. The baseline copies the previous champion.

`search_api.parse_submission(text)` validates the input. `family(parameters)` enumerates the 37 public members. `certificate_screen(parameters, all_members=False)` evaluates only the fixed-lattice temporal certificate and diagnostics, without a high-resolution reference. `screen(parameters, all_members=False)` adds an inexpensive **uncertified** density-gap estimate. `assess_member(parameters)` performs all full numerical-reference checks for one already-perturbed experiment; `assess(parameters)` performs the complete assessment. After the cheap all-member guard sweep, each visited member receives full reference validation. A verified threshold failure ends assessment with exact binary score zero; unvisited members are explicit. Only all 37 fully checked passing members receive score one. An unresolved visited reference fails closed.

`simulator.integrate(parameters, size, steps)` returns eight Fourier-field snapshots. `independent(parameters, size)` returns DOP837 snapshots and RHS count. Use `/usr/bin/python3` with NumPy/SciPy, single-threaded BLAS. The CLI wrappers set thread counts. No network, compiler, data download, or XMDS installation is required. The one-hour development budget and 660-second evaluator budget are separate.

The binary objective enables certified early rejection without changing the acceptance set. Wall allowance is 660 seconds, CPU allowance remains 400 seconds. Continuous margin diagnostics are not the official score.
