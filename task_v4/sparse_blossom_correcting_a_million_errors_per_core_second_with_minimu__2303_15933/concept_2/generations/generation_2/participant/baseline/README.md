# Actual generation-one champion

`champion.json` is copied from the operator-promoted generation-one champion,
selected from two independently passing fresh ultima-alpha attempts. It is the
actual v_2 submission, not the task builder's private feasibility artifact.
`selection.json` records the selection and `generation_1_metrics.json` records
its original independent result. `metrics.json` is its public generation-two
recheck and contains every calibration anchor.

Its original nominal score is approximately 1.0089298998. Generation two's public
score is approximately 0.9393638030: local calibration loses weight-gap and
posterior margins. Some failures are exact anchor violations, not merely
conservative certificate misses. The independent evaluator recomputes everything.

From the participant directory:

```
/usr/bin/python3 -B workspace/check.py baseline/champion.json --summary-only
```

The artifact is a permitted starting point. No optimizer, private search code,
or private stronger witness is included.
