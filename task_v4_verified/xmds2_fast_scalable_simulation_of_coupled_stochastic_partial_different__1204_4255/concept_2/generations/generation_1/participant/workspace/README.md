# Local interface

From the concept root:

```
/usr/bin/python3 participant/baseline/search.py --output attempts/baseline.json
/usr/bin/python3 participant/workspace/check.py attempts/baseline.json --quick --family
/usr/bin/python3 participant/workspace/check.py attempts/baseline.json
/usr/bin/python3 evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json
```

In a participant-only checkout, use an existing writable output directory in place of `attempts/`; the first three commands do not require evaluator files.

`search_api.parse_submission(text)` validates a witness, `family(parameters)` enumerates public perturbations, `screen(parameters, all_members=False)` returns inexpensive, **uncertified** estimates, and `assess(parameters)` computes the full public assessment. `simulator.integrate(parameters, size, steps)` returns eight Fourier-field snapshots. `independent(parameters, size)` returns DOP853 snapshots and the RHS evaluation count. `DEFAULT` is only a convenient initial parameter dictionary.

Use `/usr/bin/python3` with NumPy and SciPy. Set `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` before importing NumPy in custom programs. The CLI wrappers enforce this. No external data, compiler, network, or XMDS installation is needed. The inexpensive screen is not a reference-convergence test and does not determine acceptance.
