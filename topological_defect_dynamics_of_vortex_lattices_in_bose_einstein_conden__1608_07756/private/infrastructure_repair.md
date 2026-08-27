# Non-counted first launch

The v_01 isolated session (ultima-alpha, 211.888 seconds) exposed a discrepancy:
pytest was present for the author session but not visible in the restricted
participant runtime. The agent successfully ran the baseline and had begun to
adapt around the missing optional test runner; no substantive repaired system
was submitted. The main session terminated it rather than count any downstream
failure as evidence of hardness. Pillow, NumPy and SciPy were explicitly verified
available by that session.

v_02 preserves all numerical inputs, source code except the calibration runner,
observable definitions, metrics and thresholds. Its tests have a standard-library
unittest entry point and TASK.md no longer advertises pytest. This is an
infrastructure correction, not a fundamental redesign or difficulty revision.
The next launch is a completely new ephemeral session with only v_02 paths.
