# Shared-node damped-rational interpolation optimizer

## Run

```sh
python /path/to/submission/solution.py INPUT.json OUTPUT.json
```

`solution.py` is the complete runtime submission. It uses only the input file,
Python's standard library, NumPy, and SciPy. It works independently of the current
working directory and writes exactly one JSON object containing `nodes`.

## Method

1. Normalize coordinates by the smallest supplied damping coefficient.
2. Construct several weighted Vandermonde equilibrium initializations, retaining
   the best shared node vector under the actual scenario-wise peak objective.
3. Evaluate weighted Lebesgue functions in a scaled logarithmic barycentric
   representation. Search every inter-node interval and the exterior interval
   for every supplied scenario. Logarithmic search coordinates resolve narrow
   peaks caused by small and repeated poles; analytic Newton steps polish peaks.
4. Include the exact nodal value one. Beyond the last node plus `d+1` in normalized
   coordinates, every weighted cardinal term is decreasing, so the remaining
   infinite tail cannot contain a larger maximum.
5. Optimize logarithmic node gaps with an epigraph SLSQP minimax formulation and
   analytic gap derivatives. Derivatives use sums across each gap to avoid
   cancellation between tightly clustered nodes. An initial boundary-anchored
   solve is followed, when useful, by a solve that also frees the first node.
   That solve explicitly includes the maximum on the interval left of the nodes.
6. Retain only improved, representable candidates. A process-CPU guard leaves
   headroom beneath the execution limit, and numerical libraries use one thread.

Mixtures are used only for initialization. The final optimization controls the
maximum over all explicitly supplied scenarios, not their average.

## Validation and scratch work

The development scripts, logs, generated cases, and numerical results are kept
in this directory. `scratch/assets` contains unchanged copies of the supplied
baseline and example inputs, so the validation scripts are also self-contained.
They are not imported by the runtime solver.

- `benchmark.py`: independent, densely bracketed peak searches for the examples.
- `stress.py`: 21 deterministic degree/scale stress cases, including degree 48.
- `random_stress.py`: 32 reproducibly generated uncertain-prefactor cases.
- `edge_stress.py`: 18 empty-pole, repeated-pole, damping, and pole-count limits.
- `precision_tests.py`: 90-digit evaluation checks and finite-difference checks
  of the analytic gradient.
- `interface_tests.py`: strict JSON, representability, arbitrary-working-directory,
  8-CPU-second, and 1-GiB address-space checks in fresh processes.
- `refinement.py` and `origin_experiment.py`: additional optimization experiments.

Run development scripts from this directory. Final measured diagnostics are
recorded in `validation_summary.json`. These are independent numerical checks,
not results or certificates from the unavailable private evaluator.
