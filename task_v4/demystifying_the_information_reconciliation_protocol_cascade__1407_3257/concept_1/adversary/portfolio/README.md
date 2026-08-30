# Bounded privileged portfolio audit

This is generation-side, privileged evidence only. It is not a fresh-worker
attempt and must not be exposed to the participant. The frozen target,
participant files, evaluator files, and fixed cases were not changed.

## Outcome

Achievability remains **unknown**. The search screened 27 combinations on
128 public training frames and 72 public conditional-stress frames, then
completed one full public development evaluation. It attempted one full
hidden evaluation through the existing frozen evaluator, but that evaluation
did not finish within the 780-second overall search budget. No hidden score
or successful witness is claimed. The timed-out evaluator and its workers
were terminated by their own private process group, not the fresh runner.

The selected artifact, `policies/parity_2_passes_9.json`, uses nine passes and
parity-derived second blocks. On full development it achieves 18.8972%
overall cost reduction but only 1.5020% in the bandwidth family, below the
fixed 3% minimum. It has zero normal failures out of 1,536 frames, but two
conditional-stress failures out of 192 frames (1.0417%), above the fixed
0.5% stress limit. It is therefore **not a qualifying solution**.

The training screen also considered combinations of initial block sizes
conditioned on observable latency and cross-pass shortest-block batching.
Some clear the training cost gates, but small-sample training results are
not evidence of full-suite feasibility. The search's planned quarter-tail
and quiet-streak hypotheses were not reached before its screening cutoff;
the attempted subset is precisely recorded in `training_summary.json`.

## Evidence

- `plan.json`: predeclared runtime, resources, hypotheses, selection method,
  hidden-evaluation limit, and frozen-manifest digest.
- `training_summary.json`: all 27 attempted combinations and their scores.
- `development_summary.json`: the completed full-development score.
- `policies/`: exact JSON artifacts for attempted combinations.
- `train/` and `dev/`: detailed public-case reports.
- `hidden/parity_2_passes_9.json`: explicit bounded-search timeout record;
  it is not a completed evaluation report.
- `summary.json`: final counts, runtime, unknown-achievability conclusion,
  and successful frozen-artifact integrity check.

Execution used two workers at nice level 10 and disabled Python bytecode
writes. All new files and output were confined to `adversary/`. No fresh
agents were launched, no independent champion was promoted, and the
parent-owned empirical task status was not modified.

To complete the interrupted audit later, from the concept root:

```sh
python3 -B -I evaluator/evaluate.py --policy adversary/portfolio/policies/parity_2_passes_9.json --split hidden --jobs 2 --output adversary/portfolio/hidden/parity_2_passes_9.completed.json
```
