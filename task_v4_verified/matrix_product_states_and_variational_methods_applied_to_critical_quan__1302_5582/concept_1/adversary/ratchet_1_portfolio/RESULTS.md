# Single portfolio result: not passing

Exactly one general variant and one official frozen evaluation were run, with
zero retries and no solver changes after hidden feedback. The candidate is
43,201 bytes and contains only four Python source files, not teacher states,
case-ID branches, parameter-state tables, or cross-request storage.

The calibration SHA-256 is
`1289bafc01056df31089108460062aac04b289cdd19b7c4f483dfc01fca0e7f2`.
Candidate and frozen-asset hashes match before and after evaluation.

| Metric | Observed | Target |
|---|---:|---:|
| Score | 43.356280 | 80 |
| Core | 0.599936 | 0.80 |
| Worst family | 0.048618 | 0.70 |
| Minimum long quality | 0 | 0.55 |
| Valid stages | 15/16 | 16/16 |

## Recorded failures

The long stage of `g1_2578588da6e5e8c84d3377d4b10fc7ec` returned normally but used
40.307004 accounted CPU seconds, exceeding 40. Its protected solver wall was
42.712995 seconds and outer wall was 63.185545 seconds. Neither wall guard fired.
The grader does not include a submission-stderr field for this stage; no stderr
content is inferred. This is a recorded CPU eligibility failure, not a trusted
launcher wall-time failure.

The other odd long stage is valid but has quality 0.102893. All six non-odd long
stages have quality 1. Short stages are all valid, but their mean quality is
only 0.111161; five short outputs still have maximum bond 12 rather than 24.
Thus the problem is not solely the one CPU overrun. Holding these short
qualities fixed, even perfect long qualities would give core only 0.777790.
Even additionally granting perfect runtime credit yields score at most
78.419791. These are algebraic bounds, not additional evaluations.

The fork's symmetry-aware initialization and faster local optimization reach
the retained targets in six long runs, but its short-stage schedule and odd
optimization are insufficient for the frozen combined objective. This single
failure establishes neither full achievability nor general task hardness.

## Evidence and scope

- `evaluation.json`: untouched official report, including all sixteen stages.
- `stage_resources.json`: every official stage and its reported resources.
- `failure_analysis.json`: independently recomputed aggregate and failure bounds.
- `source_hashes.json`, `integrity.json`: candidate and frozen-source checks.
- `preflight.json`, `preflight_state_validation.json`: four valid candidate
  public preflights; one copied-baseline public run exceeds CPU and is preserved.
- `unit_tests.log`: four numerical, parity, and field-response checks passed.
- `artifact_manifest.json`: complete changed-path, size, and hash inventory.

The official grade took 13.49 wall minutes; construction through grade took
23.54 minutes. This portfolio's evaluator is finished. No fresh-attempt outputs
were read, and no participant, evaluator, calibration, target, or main status
file was modified. Main owns any subsequent decision; this sidecar stops here.
