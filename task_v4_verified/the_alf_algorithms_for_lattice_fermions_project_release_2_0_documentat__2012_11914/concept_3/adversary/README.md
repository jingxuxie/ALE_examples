# Private evaluator controls

These are validation fixtures, not fresh model attempts or eligible champions.
The parent owns participant tournaments and final task status.

- `isolation_probe/solve.py` asserts private-label and host-path denial,
  read-only public/submission mounts, public training-label availability,
  private PID/network namespaces, one CPU and the per-process memory limit.
  It outputs a deliberately weak uniform spectrum to complete the real CLI.
- `malformed_output/solve.py` includes a fabricated runtime array. The archive
  must be rejected, never used to override evaluator-measured timing.
- `nonfinite_output/solve.py` emits NaN in an otherwise correctly shaped output.
- `timeout_probe/solve.py` tests wall-clock termination with a private 0.5-second
  control limit, not a change to the frozen 120-second evaluation limit.

Run static controls from the paper-task directory:

```
python3 -B concept_3/evaluator/test_evaluator.py
```

Run process controls outside any parent sandbox that blocks nested bubblewrap:

```
python3 -B concept_3/evaluator/test_evaluator.py --process-controls
```

Reports are written to `evaluator/hidden/static_validation_report.json` and
`evaluator/hidden/process_validation_report.json`. The static oracle artifact
stays private and is never mounted into, or read by, a submitted executable.
An oracle score of 100 proves scorer consistency, not prediction achievability.
