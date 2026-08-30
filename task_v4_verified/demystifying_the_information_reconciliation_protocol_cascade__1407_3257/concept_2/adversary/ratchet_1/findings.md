# Champion-ratchet private handoff

Candidate: `n8192_b128_w18_pairs`. Status: ready for main's generation switch and two independent cold trials.

## Validity

Six fixed valid permutations, n=8192, block size 128, 64 roots/pass, 384 rows, GF(2) rank 379. The planted 18-bit even-parity core occupies nine roots per pass; six disjoint first-pass activation bits give weight 24. Both independent priority replays report initial_odd=6, corrected=6, residual=18. The byte-identical archived evaluator gives score 1.0.

## Measured search results

All 20 selected-case runs fail within their recorded caps: five 30-second probes, eleven 240-second confirmations, and four 120-second sensitivity runs. They consume 3117.7 aggregate CPU seconds. There are no solver process/validation errors. This is not a proof of absence or one-hour agent hardness.

| Case | Successes/runs | Best observed valid parity-core weight | Fastest success (s) |
|---|---:|---:|---:|
| archive_control | 6/12 | 14 | 0.970 |
| n2048_b32_w14_pairs | 3/5 | 14 | 3.283 |
| n2048_b32_w16_pairs | 0/5 | 106 | — |
| n2048_b32_w18_pairs | 0/5 | 100 | — |
| n4096_b64_w14_pairs | 0/5 | 84 | — |
| n4096_b64_w16_pairs | 0/5 | 84 | — |
| n4096_b64_w18_pairs | 0/5 | 84 | — |
| n8192_b128_w14_pairs | 0/5 | 66 | — |
| n8192_b128_w16_pairs | 0/5 | 70 | — |
| n8192_b128_w18_pairs | 0/20 | 68 | — |
| n2048_b16_w18_pairs | 4/5 | 18 | 0.430 |
| n2048_b64_w18_pairs | 0/5 | 30 | — |
| n4096_b32_w18_pairs | 0/5 | 238 | — |
| n8192_b64_w18_pairs | 0/5 | 204 | — |
| n4096_b64_w18_quartets | 1/5 | 18 | 2.282 |
| n8192_b128_w18_quartets | 1/5 | 18 | 1.053 |
| n4096_mixed_w18_pairs | 0/5 | 98 | — |

Rows include calibration runs on the archive control; other cases receive five probes unless selected for confirmation. A recorded parity core heavier than 18 is not a valid activated witness. Different instances use distinct construction seeds; cross-case comparisons are suggestive rather than isolated causal estimates.

## Why this is a genuine search challenge

Archived and adapted grouped solvers recover the same original core in 2–3 seconds with identical complete BEST traces. Standard BP also has an identical 20-update calibration trace. On the same 8192/128 geometry, the quartet-spread 18-bit control solves with BP in 1.05 seconds. Thus dimension support is demonstrably working, and changing labels of an old witness is not the tested failure mode.

For the selected pair-spread core, nine roots carry two bits each. A rank-379 information set covers fewer than three complete 128-bit roots; grouping is scaled to two, with additional global/zero and three-root controls across passes. The grouped decoder's low-order nonpivot enumeration and BP/OSD's sparse-impulse guidance do not find a <=18 parity core under these tested budgets. The randomized-order BP sensitivity avoids relying solely on the champion's deterministic high-overlap impulse ordering. These are mechanism-based interpretations, not complexity lower bounds.

## Artifacts and exact adaptations

- `deployment.json`, `privileged_witness.json`, `manifest.json`: main's candidate deployment, private certificate input and integrity manifest.
- `ready.json`, `selection.json`, `independent_score.json`, `validation.json`: ready metadata and positive checks.
- `search_results.json`, phase plans/results, and `runs/`: all seeds, wall/CPU caps and use, commands, stdout/stderr, generated cores, successful witnesses and failures.
- `cases/`: all seventeen deployments and private constructions, including successful easy controls.
- `root_cause_clusters.json`, `adaptation_details.json`, `sources/*.patch`, `bin/*/geometry.hpp`, `bin/*/compile.json`: empirical clusters, exact adaptation descriptions, actual unified diffs and build commands.
- `trajectory_calibration.json`, `archive_integrity.json`: original/adapted trace agreement and unchanged archive source hashes.

## Reproduction

Run from this directory, using Python 3 and g++ with libz3 available:

```sh
python3 -B sweep.py prepare
python3 -B sweep.py sweep --seconds 30 --workers 16
python3 -B sweep.py confirmation --case n8192_b128_w18_pairs --seconds 240 --workers 11
python3 -B sensitivity.py --seconds 120
python3 -B finalize.py
```

Existing run result files are reused, not silently overwritten. To collect a new replicate, use a new phase/label and recorded seed via run_job. Preparation regenerates deterministic case data and binaries only inside this worker directory. Main owns the real generation switch and cold agents; this worker does neither.
