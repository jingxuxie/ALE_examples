# Private generation-1 achievability sidecar

This directory is host-only. The current 325-waveform contract is already frozen;
this experiment does not alter it or make a hardness finding. The sole warmstart
is the original generation-0 fresh champion in `champions/generation_1`.
No active v2 artifact, transcript, log, or score is inspected.

## Method

`search.py` recomputes the original champion on all 325 waveforms using the trusted
worker and its independent exact-state oracle. It selects limiting signed
successive-cap differences and exact-error constraints, then refines the six
control knots by finite-difference sequential linear programming. Trust regions,
three step fractions, full-suite constraint discovery, and seeded local restarts
limit reliance on a local linear approximation. Depth stays at 24. Every tested
candidate is validated by the unchanged physical waveform protocol.

Only actual exact/MPS circuit evaluations contribute to objective values. Public
error and spread thresholds are unchanged. Partial active-family success is never
reported as a passing witness: a full 325-waveform run and the existing independent
trusted checker must both pass. The checker is run after the search worker pool
has closed, never concurrently with another sidecar simulation pool.

The run uses at most four simulation workers, each with one BLAS thread, and a
single-threaded linear-program solver. The search budget is 560 seconds; final
trusted grading is additional. No model calls or other agents are used.

```bash
python adversary/achievability_generation_1/search.py --seconds 560
```

## Evidence

- `history.jsonl` and `search.log`: chronological experiments and progress.
- `full_suites/`: full recomputations of the warmstart and selected refinements.
- `best/witness.json`: best full-suite candidate, not merely the best active subset.
- `best/trusted_score.json`: unmodified trusted checker output on that artifact.
- `result.json`: actual score, passing flag, counts, timings, and preservation result.
- `preservation_before.json`, `preservation_after.json`: SHA-256 snapshots of all
  frozen assets, status/freeze/report metadata, original champion files, and the
  generation-zero archive manifest.

All new artifacts and logs stay inside this directory. Previous fresh code and
pulses remain private. A passing grade establishes achievability of this finite
frozen suite only; it is not a certificate for every point in the continuous drift
box or a falsification of the original paper.
