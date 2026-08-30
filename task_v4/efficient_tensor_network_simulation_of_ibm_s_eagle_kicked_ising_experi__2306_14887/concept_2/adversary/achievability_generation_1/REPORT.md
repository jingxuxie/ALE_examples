# Passing private witness for the frozen generation-1 target

**Achievability established for the frozen 325-waveform finite suite.**
The unchanged trusted checker returns `valid=true`, `passed=true`,
`evaluation_complete=true`, core **100**, worst-family **100**, resource **50**,
and depth **24**. No target, participant, evaluator, or status change was made.
This is a privileged warmstart result, not a fresh-agent result or hardness claim.

## Artifact and independent grading

- Witness: `best/witness.json`.
- Full trusted result: `best/trusted_score.json`.
- Witness SHA-256: `34d4d38d72854d49f0cf50382abfd50d4b85181028a69fee2a59c8d146311763`.
- Target SHA-256: `6fa4aba2f0f0207c3882ac10dbc227d3f901fd27964085db1dd8eabdeac331ef`.
- Minimum exact error: **0.154380783524826**, family `corner_23/tilt_plus`;
  margin above 0.15: **0.004380783524826**.
- Maximum successive-cap spread: **0.007895612538128**, family `corner_20/tilt_plus`;
  margin below 0.008: **0.000104387461872**.
- All 325 exact/error/spread/score values match the search's full-suite recomputation
  exactly. The artifact was graded by the existing checker CLI, not by a substitute.

## Search and resource accounting

The sole warmstart was the original generation-0 fresh champion in
`champions/generation_1`, which independently reproduced worst-family score
89.49005774367336 on this frozen target. An active-family trust-region linear
refinement varied only its six knots. Full-suite checks exposed missing limiting
corners, which were then added to the active constraints. Three of five attempted
refinement steps were accepted. The second refined full-suite candidate passed.
The configured seeded random-restart fallback was never needed (zero restarts).

- Distinct tested knot vectors: **34** (including finite-difference probes).
- Search waveform evaluations: **1500**, each with one independent exact
  circuit and three actual MPS circuits; **4500** search MPS evolutions.
- Full-suite search evaluations: **3**, including the original warmstart.
- Additional trusted checker evaluations: **325** waveforms, **975** MPS evolutions.
- Search runtime: **206.183 seconds**; trusted checker:
  **48.961 seconds**; combined measured runtime:
  **255.531 seconds**. Search stopped early after finding a pass.
- Maximum concurrency: **4 simulation workers**, each with **1 BLAS thread**.
  The linear-program solver was single-threaded. Search and checker pools did not overlap.
- Model calls and fresh launches: **0**. No active v2 files were read.

## Preservation and interpretation

All **48** recorded SHA-256 preservation hashes match before/after and the
final handoff check, including frozen public assets, trusted resources, target,
status/freeze/report metadata, the private original champion, and archive manifest.
New files exist only under `adversary/achievability_generation_1`.
Raw original fresh code and pulses remain private. `evidence_integrity.json`,
`preservation_before.json`, `preservation_after.json`, and `evidence_manifest.json`
provide the audit trail; `history.jsonl` records unsuccessful experiments honestly.

This establishes existence for the already-frozen discrete suite, not every point
inside the continuous calibration box. It remains a stress test of the supplied
finite-bond convergence heuristic, not a falsification of the original paper.
Only main decides subsequent status or hardness findings from fresh-attempt results.
