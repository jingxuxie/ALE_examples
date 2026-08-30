# Privileged freeze validation

Date: 2026-08-28. No fresh agents launched. All files are within concept_2.

## Tested

- 48 hidden pytest cases pass. The final run reports 7.10 seconds wall time on
  the loaded host; tests are single-threaded. An earlier 47-test run took 2.12
  seconds before the regular-file validation case was added.
- Exact recurrence checked independently against symbolic Chebyshev values.
- Normalized Rayleigh invariance under rational vector scaling checked.
- Positive, wrong-direction, and roundoff-depth evidence cannot score.
- Duplicate keys, booleans/floats, oversized integers/fractions/files, excessive
  JSON depth, nonfinite values, invalid UTF-8, ragged shapes, symmetry/trace,
  degree, vector, point, noncommutation, and principal-minor failures rejected.
- Six PSD controls accepted in all three profiles: constant, rank-deficient
  moving Gram block, and four degree-varied strictly positive coupled blocks.
- Narrow rotated quadratic misses a 257-node uniform mesh but is rejected by
  all full profiles. Layer-isolation tests also demonstrate determinant-layer
  detection with only 17 mesh nodes and adaptive/local detection with the
  determinant stage disabled. Those ablations occur only in tests.
- Public module shims and adjacent Python files do not affect grading. Private
  hash drift fails closed. A mocked-guard scoring-unit test is explicitly a
  plumbing check, **not** a successful scientific witness.

## Private search pilot

24 eligible coupled-branch candidates: four polynomial orders (2,4,7,11),
three nearby-branch gaps (1e-8,2e-6,3e-4), and two seeds. All have independently
checked exact negative Rayleigh evidence. No profile was fooled by these
candidates. Detailed stages and CPU measurements are in `control_report.json`.
Controls plus sweeps consumed approximately 1.10 CPU seconds, excluding Python
startup and imports. This is a bounded sanity pilot, not a hardness proof.

An initial degree-four generator family (order 1) failed the anchor
noncommutation constraint. That private sweep stopped rather than counting
invalid samples as evidence of difficulty. It was replaced with eligible
order-2 candidates; **the numerical guard and thresholds were not weakened or
strengthened** in response to any witness. No easy accepted witness was found.
The final exact checker additionally rejects nonregular files before reading.

## Baseline result

Default four-trial search writes a degree-24 admissible witness. Exact quotient
is approximately `-2.9966e-7`; all three guard profiles detect negativity.
`valid=true`, `evidence_valid=true`, `passed=false`; core, worst-family, and
runtime scores are all zero. The isolated evaluator used approximately 0.315
CPU seconds. Full rational evidence and diagnostics are archived in
`attempts/baseline_score.json`. The public `input/example_rejected.json` is the
same data, clearly labeled as rejected, not a solution.

## Interpretation

The package is freeze-ready for the main worker's first fresh attempt.
`hard_open_candidate` is provisional candidate status only. There is no known
successful witness and no assertion of existence, impossibility, or final hard
classification. Read-only private deployment is required for immutability;
hashes alone are not a replacement for that boundary.
