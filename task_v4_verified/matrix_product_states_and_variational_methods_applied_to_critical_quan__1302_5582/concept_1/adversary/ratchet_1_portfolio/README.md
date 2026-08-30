# One bounded generation-time portfolio

This sidecar contains exactly one general solver variant and permits one frozen
evaluation. It is not a fresh participant attempt. No ongoing attempt outputs
are read, and no participant, evaluator, calibration, or target file is changed.

The fork starts from the published g0 champion. It replaces dense environment
and one-site contractions with the same operator applied sequentially, moves
the orthogonality center with QR rather than SVD when no truncation is needed,
and initializes unrestricted requests from a parity-even zero-field state.
Nonzero fields are included in every subsequent optimization update; no field
case is constrained to an even sector. Parity constraints remain exact when
the request explicitly specifies them. All physical basis states are retained.

`v1/` is the self-contained submission. It contains no requests, cached states,
reference energies, hidden labels, parameter tables, or cross-request storage.
`provenance/published_baseline/` preserves the public source before the fork.
Preflight results, source hashes, and the single official report are kept here.
Only the complete frozen evaluator can establish resource-feasible achievability.
