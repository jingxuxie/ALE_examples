# Native parity-walk submission

The evaluated artifact is `submission/witness.json`. It contains one native CNOT
circuit for each of the six public instances, without metadata or auxiliary
operations.

## Validation

Run these commands from this solution directory:

```sh
python3 dev/collect.py
python3 dev/validate.py
python3 dev/audit.py
```

The collector retains the best independently valid circuit found for each case.
The audit checks strict JSON structure, physical edges, every required parity,
the ordered output rows, CNOT count, and the specified endpoint-resource depth.
It also independently simulates every computational-basis input column. Final
per-case results and aggregate scores are recorded in `dev/final_audit.json`.

## Development

The search combines native Steiner-tree parity computation, bidirectional beam
search, parity-preserving local exact resynthesis, commutation-aware scheduling,
and structural optimization of critical paths and wire loads. Development
sources, search logs, candidate circuits, and an unchanged copy of the public
instances are under `dev/`. No development executable is needed to evaluate the
static witness.
