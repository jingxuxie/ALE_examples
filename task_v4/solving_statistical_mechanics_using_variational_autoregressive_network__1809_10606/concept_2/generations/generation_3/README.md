# Concept 2, generation 3: one-percent local exploration floor

This self-contained mode-B candidate is `built_not_tested`. Generation 2 remains
solved. The sole scientific change is row L1 <= ln(99), giving every binary
conditional outcome probability at least 0.01. All seven physical gates, the
beta interval [1,3], binary couplings, and architecture remain unchanged.
General attainability is UNKNOWN; no passing generation-3 witness is known.

Expose only `participant/` to the participant. Keep evaluator, tests, adversary,
attempts, champions and status organizer-only. This package does not launch agents
or modify prior generations. From this directory:

```
python -B participant/baseline/run.py --output adversary/baseline_replay
python -B evaluator/evaluate.py --submission participant/baseline --output adversary/baseline_report.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m unittest discover -s tests -v
```

The public runnable baseline is only the actual completed Generation 2 champion
with its weights rescaled; it does not use private optimized audit candidates or
participant optimizer source. Private rationale is archived in `adversary/`.
Commitments are in `evaluator/freeze.json` and `adversary/release_manifest.json`.
