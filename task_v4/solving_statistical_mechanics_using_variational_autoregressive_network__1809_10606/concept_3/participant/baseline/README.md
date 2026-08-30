# Weak baseline

From the participant root run `python baseline.py --output "$OUTPUT_DIR"`.
This deterministic baseline emits exactly float64 `(24,64)` probabilities and
`<U24` query IDs. It uses no hidden parameters or labels. Its source remains in
the parent directory so this folder contains no stale precomputed predictions.
