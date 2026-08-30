# Generation 3 is frozen and ready

**Generation `population-witness-v3-robust`; ratchet count two.** Main may launch
both full one-hour fresh B attempts. No agents have been launched by this worker.

Expose only the active `participant/` subtree. All earlier attempts, champions,
their code, private witnesses, evaluator, and audit records must remain outside
the fresh workspace. The active hashes are this directory's `freeze.json` and
`evaluator_freeze.json`; earlier manifests and snapshots are immutable history.

## Frozen contract

- The same base JSON format and one primary mode-B population-violation target.
- Base plus both signs of all 120 symmetric pair-matrix coordinate axes: **241 points**.
- Off-diagonal axes are divided by sqrt(2); all axes have unit Frobenius norm.
- Radius **0.001**, chosen after testing 0.001, 0.002, and 0.003.
- Every generation-two physical bound, including DAD <= 0.001 and violation
  >= 0.02, holds at every point. Each point has its own original 65-point path.
- All perturbed matrices must be in the original domain. No projection/clipping;
  invalid neighbors are separately labeled domain failures, never physics evidence.
- The score is the minimum population violation over all 241 certified points.
- Trusted evaluator wall limit **900 seconds**; fresh search budget stays one hour.

Both old fresh champions fail physically inside the valid stencil. The large
witness has 221 DAD and 122 energy failures; the second has four DAD and 30 energy
failures. No stencil point of either witness is out of domain at radius 0.001.
Original old scores, snapshots, and champions remain unchanged.

## Validation and preliminary achievability

The zero-interaction nonwitness completes all **241 independent path certificates**
and remains admissible but score zero, in about 58 seconds on the calibration run.
Stencil geometry, independent construction, original-threshold preservation,
and historical hashes are checked in `basic_audit.json`. The expanded numerical
and 44-case malformed/security suite also **passes**, recorded in `robust_audit.json`.

A privileged private warm start **passes all 241 endpoint screens and all 241
independent path certificates**, with official worst population violation
0.02044251634925809, maximum DAD 0.00048733050993875806, and maximum energy error
0.00006660768678612428. The isolated trusted evaluator reports score 1.0 and
`robust_witness_verified` in `private_centered_evaluation.json`; runtime was
216.03 seconds, well within the generous 900-second limit. Achievability is
therefore verified, not merely open. No thresholds changed after freeze.
This uses privileged earlier author data and is never a fresh-agent solution;
neither the artifact nor its source seed may be exposed. Fresh difficulty remains
for main's two independent one-hour runs to establish.

## Official invocation

```
python -I evaluator/evaluate.py /absolute/attempt/submission.json \
  --submission-dir /absolute/attempt --output /trusted/generation_3_report.json
```

The trusted parser rejects symlinks, outside-directory paths, malformed schema,
and nonfinite data. The evaluator constructs the stencil itself and does not
trust submitted neighbor amplitudes, directions, diagnostics, or scores.
