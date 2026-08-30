# Runnable baseline

From the participant directory:

```
/usr/bin/python3 baseline/solve.py --input input/examples/drifting_priors --output /tmp/fleet-policy.json
```

The deterministic baseline evaluates 32 shared-design choices, starts with
feasible minimax open-loop actions, and greedily allocates adaptive policies
to high-loss rings using averaged priors and residual branch capacities.
It uses the supplied exact catalogs and emits policies only. Its hidden scores
are frozen by the evaluator. `fleet.py` supplies the reader, route access,
catalog-based policy statistics, and objective calculation for development.

To submit this baseline unchanged, copy both Python files into the submission
directory. There are no imports from outside that directory. The official
checker is independent of these utilities.
