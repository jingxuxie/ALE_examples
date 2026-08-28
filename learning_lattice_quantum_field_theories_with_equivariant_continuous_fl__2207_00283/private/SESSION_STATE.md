# Historical author checkpoint — superseded

The checkpoint below is retained as a historical work log. All four scored
fresh attempts have since completed and solved their frozen contracts.
All ten scalar refinement cases have completed; their continuum qualification
does not justify a ratchet. Current results and the rejection decision are in
`../REPORT.md`, `../selection.json` and `tournament.json`. Final consistency
checks and refined-oracle diagnostic rechecks are recorded separately; do not
resume the old outstanding jobs or interpret this historical list as current.

The objective remains active. Do not declare a hard task unless the user's
reference >0.9, fresh mean <0.7, substantive core failure and CEGIS gates hold.
Exactly four pilot concepts were built; do not build a fifth. No ratchet has
yet been justified or consumed. Public participants are frozen.

## Scored primary sessions

All primary sessions started around 2026-08-28 01:05:45 UTC, use the supplied
allowlist runner, ultima-alpha/xhigh, empty initial output directories and a
3600-second timeout. Earlier interrupted prefix sessions are excluded; see
LAUNCH_AUDIT.md. Pilot01's TASK-only edit predates the scored restart, and its
updated frozen hash has been recorded without changing public content.

- 01_adjoint_composition: still running at the last checkpoint, stress-testing
  extreme nonlinear cases beyond the ordinary pool. Do not interrupt early.
  Main session 3279 owns all four pilot timeout wrappers; session 13675 waits
  for primary exits and evaluates 01/02/03 automatically.
- 02_fourier_transport: finished after 869 seconds; score 0.9499999704,
  worst family 0.9499999169, official anchor 0.95. All 11 hidden cases pass.
  This is solved, not a hard candidate. NumPy FFT plus exact metadata and
  analytic sensitivities provide a universal tested solution.
- 03_gauge_transport: finished after 1232 seconds; initial mean 0.9980375775,
  worst family 0.9934250593. Near-center challenge mean 0.9924198548, worst
  0.9688342996. No substantive failure. Further structured covariance and
  exact-stationary-state stress probes are being checked, not a ratchet.
- 04_scalar_checkpoint: finished after 1467 seconds; initial mean
  0.9969799681, worst 0.9963235121. Challenge mean 0.9911593335, worst
  0.9863281100. All numerical groups essentially exact; scores are limited
  by the smooth runtime factor. Strong actual isolated author anchor is
  0.9708737864; candidate is faster. This appears solved.

## Outstanding tools/checks

- 13675: watch/evaluate 01 after its primary exit, then ends. 02 and 03
  already scored successfully. Pilot01 evaluator also supports --pool challenge.
- 78306: corrected private/stress.py for gauge; builds three structured
  probes and validates the stationary reference against 512 steps and an
  analytic time integral. A metadata name collision in the first validation
  attempt was fixed; it was not a model or numerical failure.
- 23386: isolated gauge stress evaluation, report private/stress_report.json.
- 68456: scalar 100-vs-200-step refinement check, report
  private/reference/refinement_validation.json; inspect .exit and .log.
- 75718: scalar initial and challenge evaluations completed successfully.
- 11409: result collector; rerun private/collect_results.py after final scores.

All three builder subagents are closed. The scalar builder's former host
pipeline PID 1393178 completed; no need to run its long dense baseline again.
Scalar dense baselines timed out in full transport. Gauge full-coordinate
Hessian baseline took 110.96 seconds, peaked at 8,296,480 KiB, and scored
0.11919 with sensitivities absent; report retains that limitation.

## Required finish

Wait for pilot01 to finish or reach its full one-hour cap, score its challenge
pool, inspect core failures versus clerical issues, and rank all four using
worst-family performance with their strong anchors. Only natural failures
can justify retaining/ratcheting. If all remain solved, reject the tested
paper-task designs rather than inventing edge cases or tightening tolerances.
No second fresh run is warranted for a concept rejected for lacking a genuine
failure region; explain that conditional phase skip explicitly in the report.

Write REPORT.md and selection.json at the requested output root, finish
artifact/source/public-hash audits, ensure no required validation is still
running, complete the plan, and mark the goal complete only then. Include all
eight candidate directions (private/candidate_gaps.md), four pilots, scores,
shortcuts, counterexample evidence, ratchet counts, reference checks, launch
audit and acceptance/rejection rationale. Do not label any currently solved
pilot as frontier-hard.
