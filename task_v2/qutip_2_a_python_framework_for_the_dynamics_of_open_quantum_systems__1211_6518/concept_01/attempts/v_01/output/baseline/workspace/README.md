# Migration workspace

From this directory:

```
PYTHONPATH=. python -m pytest -q tests
bash run.sh campaign ../input /path/to/your/output/baseline
```

The baseline has deliberately limited physical models and migration defects.
The coefficient and spectrum loaders are schema definitions and are correct;
their use by propagation is a separate concern. Keep input formats compatible.

`experiment.py` is a reusable evidence harness, not a physical solution. It
compares final observables and refinement differences, records measured time
and memory, and truncates the resonator basis for a scaling experiment. It does
not establish physical accuracy. `engine.py`, `propagation.py`, and `process.py`
are the main replacement/repair boundaries; additional modules are welcome.
