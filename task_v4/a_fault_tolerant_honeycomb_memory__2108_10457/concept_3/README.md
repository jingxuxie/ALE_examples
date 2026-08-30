# Concept 3: controlled-data prediction (D)

Participant entry point: `participant/TASK.md`; detailed contract: `participant/workspace/INTERFACE.md`. Give contestants only `participant/`; the full original ancillary download and all held-out counts stay under `evaluator/hidden/`.

Build once from the exact original download with `python -B authoring/build_prediction.py` from the task directory. Rebuilding after freeze is refused. Evaluate a submission with `python -B concept_3/evaluator/evaluate.py --submission PATH --output RESULT.json`. The default submission is the supplied baseline. Evaluator exit code 1 means invalid execution/output; a valid but below-target prediction returns a normal JSON result with `success: false`.

The fixed score is uncertainty-adjusted worst-family extrapolation accuracy, not improvement over a baseline. The threshold, source hash, data, scoring, and sandbox are frozen before evaluation. The builder never imports the baseline. All thresholds and the complete output schema are visible to the participant.

Original data are publicly distributed empirical simulations, not hardware experiments or cryptographically secret data. The generator provenance explicitly records the residual pretraining-contamination caveat. Closed-data filesystem and network isolation are required throughout the contestant run, not just while executing `solve.py`.

The earlier preparation note proposed raw deviance scoring. The implemented protocol deliberately uses log-distance to a 1000:1 likelihood-support interval instead: its factor-two success threshold has a direct accuracy meaning while accounting for unequal sampling precision and zero-event upper bounds. This choice is fixed before the first baseline run. The 780/612/80 split and raw full-experiment probability target are unchanged.

The mandatory `evaluator/prediction_frozen.json` additionally protects scoring and the shared sandbox. The generic `authoring/freeze.py` may regenerate `evaluator/frozen.json`; both manifests are checked. The requested uppercase-document and result-field compatibility revision preserves the original threshold/data freeze and is recorded in the prediction manifest.
