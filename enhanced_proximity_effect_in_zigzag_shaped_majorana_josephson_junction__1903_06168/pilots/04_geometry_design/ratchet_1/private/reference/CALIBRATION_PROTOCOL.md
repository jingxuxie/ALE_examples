# Frozen three-case ratchet calibration

All three cases are preregistered and retained regardless of source performance:
`lower_offset`, `central_offset`, and `high_density`. Each exposes its exact
three operating points. No request, scenario, public file, source geometry,
physics helper, or evaluator is changed by this run.

From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -B run_calibrations.py --wall-seconds 900
```

The runner executes the unchanged evaluator CLI from the private directory:

```sh
python -B -u evaluator.py --calibrate --case CASE --workers 3 --output reference_runs/CASE.json
```

Three controllers run concurrently. The entire lower-offset process family is
pinned to CPUs 64–69, central-offset to 72–77, high-density to 80–85. Each uses
three process workers and one BLAS thread. All numerical processes share a
900-second wall deadline; process groups are terminated at expiry. The runner
uses CPU 69. Each process has a 4 GiB address-space cap. Affinity and process
thread counts are sampled in `../reference_runs/resource_snapshots.jsonl`.

The evaluator measures the frozen achieved public baseline (not the older
original zigzag) and exact author epoch-800 source mask, sequentially by design,
three scenarios in parallel per design. Every complete scenario has 51 momenta
and an independent Pfaffian invariant. Only the unchanged evaluator decides
physical feasibility and normalization validity. Its full gap curves and Q
are retained in the per-design measurement checkpoints and calibration JSON.

R = 0.5 mean(scenario gaps) + 0.5 minimum(scenario gaps). Anchors must be
physically feasible and strong-minus-weak must exceed 1e-4 meV. Scores are
unbounded, with the frozen baseline at 0 and source at 1 when valid. Negative,
invalid, or incomplete anchors are reported without dropping or resampling
cases. A losing source may make the evaluator exit before its final output;
existing complete measurement checkpoints remain authoritative and are
preserved in a non-ready diagnostic calibration by the validation script.

The reference-score check uses the existing evaluator's normalization and
aggregation functions on stored full-resolution anchor measurements. It is not
a second forward evaluation or a submitted-solver run. No fresh agent is launched.
