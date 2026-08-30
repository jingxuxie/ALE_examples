# Development harness

From the participant directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 input/local_simulator.py baseline --episodes 4 --seed 7241
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 input/local_simulator.py /path/to/submission --episodes 8 --seed 8123 --output /tmp/development.json
```

This standalone harness runs **trusted local code without filesystem isolation**, with the same numerical model, budgets, strict protocol, output caps, and process resource limits. It starts the 20-second timer when spawning the plain script; there is no sandbox setup to exclude. It reveals synthetic development parameters after each episode. Never use it on private evaluation episodes or untrusted submissions. Official scoring instead invokes the shared bwrap sandbox, excludes sandbox setup via a trusted wrapper marker, exposes neither parameters nor seeds, and starts a new sandbox for each episode. Its 32 episodes use independent seeds from these development examples.

`model.py` exposes `hamiltonian(parameters)`, batched `unitaries(parameters,times)`, `compile_experiments(experiments)`, `probabilities(parameters, experiments_or_batch)`, `draw_parameters(rng,family)`, and input validation. Parameters are a nine-element NumPy array in `config.json` order. Experiment dictionaries match `PROTOCOL.md`; forward prediction ignores the shots field. `runtime.py` implements the shared parent-side interaction and aggregate metric. Controllers may import these public modules but receive no evaluator state.
