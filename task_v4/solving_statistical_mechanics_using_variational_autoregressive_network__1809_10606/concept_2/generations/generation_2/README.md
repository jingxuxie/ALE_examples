# Concept 2, generation 2: operational exploration floor

This is a self-contained mode-B `hard_open_candidate`. Generation 1 remains
solved; this separate mission changes only the row L1 bound from ln(9999) to
ln(999). The seven physical gates and beta interval are unchanged. General
attainability is UNKNOWN; there is no known passing generation-2 witness.

Expose only `participant/` to the participant. Keep `evaluator/`, `tests/`,
`adversary/`, `attempts/`, `champions/`, and `status.json` organizer-only.
This package launches no agent and makes no changes to the original generation.

From this directory:

```
python -B participant/baseline/run.py --output adversary/baseline_replay
python -B evaluator/evaluate.py --submission participant/baseline --output adversary/baseline_report.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m unittest discover -s tests -v
```

`evaluator/freeze.json` commits the specification and trusted evaluator code.
`adversary/release_manifest.json` commits the validated release files.
