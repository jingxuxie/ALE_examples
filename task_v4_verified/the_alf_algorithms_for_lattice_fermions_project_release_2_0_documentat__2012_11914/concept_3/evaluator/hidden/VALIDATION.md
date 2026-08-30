# Private validation handoff — August 28, 2026

Participant source/data and frozen targets are unchanged by private validation.
`status.json` is already `pending_tournament`; parent owns all fresh attempt
scores, champion decisions and final status. These controls are not attempts.

## Results

- Frozen baseline heldout: core 75.2338563236265, worst family
  48.73553181385645, wall time 9.647068970953114 s; valid, does not pass 90/85.
  Source: `baseline_heldout_report.json`.
- Static tests: 18 malformed output/array/archive conditions rejected.
  Oracle artifact scores approximately 100/100 using trusted static scoring.
  No submitted process reads or receives oracle labels. This is an evaluator
  positive control, NOT demonstrated prediction achievability.
  Source: `static_validation_report.json`.
- Data audit: 1,920 distinct IDs and spectra across three independent splits;
  every covariance is SPD. Heldout mean whitened squared residual is
  55.309718541998365 for 56 observation dimensions. Extreme-beta stable kernel,
  endpoint sum rule and exact disjoint-bin Wasserstein checks pass.
- Real bubblewrap control: hidden labels/generator/calibration/status and
  host paths denied, including attempts via proc-root; public labels readable;
  public and submission mounts read-only; PID/network isolation and one CPU /
  per-process address-space limit asserted. The deliberately uniform output is
  valid but scores 0.27664413550932365 / 0.016576584165542772 and does not pass.
- Real malformed process controls reject an extra self-reported runtime field
  and a NaN in an otherwise well-formed archive. Private 0.5-second timeout
  control is terminated, reporting 0.8083434259751812 seconds including kill
  and reap overhead. The official deadline remains unchanged at 120 seconds.
  Source: `process_validation_report.json`.
- Launcher-only CPU/RSS diagnostic names and scope were corrected in the
  evaluator and historical private reports; scientific scores and authoritative
  measured wall times are unchanged. No aggregate-worker usage is claimed.

## Reproduction

Run from the paper-task directory:

```
python3 -B concept_3/evaluator/test_evaluator.py
python3 -B concept_3/evaluator/test_evaluator.py --process-controls
python3 concept_3/evaluator/evaluate.py --submission concept_3/participant/baseline --output concept_3/evaluator/hidden/baseline_heldout_report.json
```

The last two commands need a host context permitting bubblewrap namespaces;
this environment requires escalation outside the parent sandbox. No unsafe
fallback is used. Static controls do not execute any submitted process.

## Changed private paths in this validation phase

- `evaluator/runtime.py`: launcher-only diagnostic names/scope, no target change.
- `evaluator/test_evaluator.py`: static and sandboxed process controls.
- `evaluator/hidden/{static_validation_report.json,process_validation_report.json,oracle_control_predictions.npz}`.
- `evaluator/hidden/{calibration.json,baseline_heldout_report.json}`: collected
  measured results and corrected diagnostic labels, not retuned thresholds.
- `evaluator/hidden/{PROVENANCE.md,VALIDATION.md}`: private documentation.
- `adversary/{README.md,isolation_probe/solve.py,malformed_output/solve.py,nonfinite_output/solve.py,timeout_probe/solve.py}`.

No participant files, frozen targets, generator, fixed split manifest or
hidden-label files were modified in this phase. No agents were launched.
