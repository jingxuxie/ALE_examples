# Local interface

Run from the generation root:

```
/usr/bin/python3 -B participant/baseline/search.py --output attempts/baseline.json
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --guards --family
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json --quick --family
/usr/bin/python3 -B participant/workspace/check.py attempts/baseline.json
/usr/bin/python3 -B evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json
```

`search_api.parse_submission`, `family`, `certificate_screen`, `screen`, `assess_member`, `reference` and `assess` are importable. `simulator.quick` provides an uncertified inexpensive screening reference, never acceptance. `assess_member` assesses one already-perturbed parameter dictionary. `assess` assesses the entire explicit protocol family.

Default full checks prioritize exact diagnostic guard failures, then fully validate a reference before any certified early rejection. A pass requires every one of the 69 members. `--exhaustive` on the checker/evaluator, or `assess(parameters, exhaustive=True)`, also visits remaining members after threshold failures. An unresolved reference still stops as invalid. Exhaustive mode does not change scoring.

The evaluator accepts data only, uses its private frozen copy, and returns one finite objective JSON with exact binary score, validity, reason, per-member uncertainty, completeness and resource information. Wall/CPU limits are 1500/900 seconds, memory 1536 MiB, one numerical thread. Development budget is 3600 CPU seconds. Python 3 with NumPy and SciPy is sufficient.
