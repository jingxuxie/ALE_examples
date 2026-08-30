# Frozen v2 diagnostic conclusion

Exactly one unchanged official replay and one relaxed-CPU isolated diagnostic were run. No source optimization, fresh agent, generation change or root/status edit was made. Protected tree plus both frozen submissions unchanged: **True**.

## Termination evidence

- Initial official result: exit 137, 128.805497 measured CPU seconds, no worker log, no watchdog.
- Unchanged official replay: exit 137, **132.927369 measured CPU seconds**, 439.819 wall seconds, no watchdog.
- Replay worker's observed soft/hard CPU limit remained 133 seconds; it had one thread. The last live Linux CPU-clock sample was {'prof': 133.028, 'virt': 132.024, 'sched': 132.464901108}.
- This reproduces the near-limit kill. The replay's measured CPU exceeds the original 132-second score cap, independently of the initial sub-cap measurement. Linux 5.15's PROF-based hard limit and the other accounting observations are distinct; the initial 128.805497-second result alone was not proof of a numerical overrun. The exact signal sender in the initial run was not traced.

## Full quality and original targets

- Completed relaxed run: **427 -> 384 failures / 3072 shots**, reduction 10.070258%.
- Holdout reduction: 12.093023%. Worst-family reduction: -3.539823%.
- Family failures: known_nonuniform_crosstalk: 113 -> 117; overlapping_spatial_pairs: 108 -> 98; space_time_pair_memory: 206 -> 169.
- Paired absolute 95% interval: [0.005474234987149249, 0.02252055667951742].
- Full-run resource: **156.480366 CPU seconds**, 462.067 wall seconds, 114360 KiB peak RSS; watchdog False.
- Compared with the original 132-second numerical cap: +24.480366 seconds. Confirmed completed-run numerical overrun: True.
- Failed original quality gates: pooled_improvement, independent_holdout, family_nonregression.

Conclusion: **NOT_QUALIFIED: original replay is invalid; completed diagnostic fails original numerical gates**. The relaxed run is nonqualifying and does not replace the official result.


## Scope and raw evidence

Mandatory bwrap isolation, seccomp, private PID/network namespaces, data, model parameters, case order, native binary and all quality gates were retained. Only the private in-memory diagnostic ceiling changed to 180 CPU seconds, giving worker RLIMIT_CPU 181. The 900-second worker wall watchdog was unchanged. No driver watchdog fired: True.

Raw scores: `official_replay.json` and `relaxed_diagnostic.json` (nested `evaluation` contains the complete paired scores). Predictions and the diagnostic worker response are in `relaxed_worker_outputs/`. Process and CPU-clock observations are in `*_processes.jsonl` and `cpu_clocks.jsonl`. Full source/freeze hashes are in `integrity_before.json` and `integrity_after.json`.

The frozen development log reports 130.12430454 seconds of decode/construction CPU, but its bench excludes imports and uses development data, not this official hidden replay. It is context, not a qualifying measurement.

All changed files are confined to `concept_1/adversary/second_attempt_diagnostic/`. The original `v_2_result.json`, frozen targets and status remain untouched. Main owns adjudication; this diagnostic is not a promotion or a retargeting.
