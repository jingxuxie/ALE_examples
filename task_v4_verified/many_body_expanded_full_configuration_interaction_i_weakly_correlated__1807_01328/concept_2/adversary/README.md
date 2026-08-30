# Private author calibration

Never expose this directory to fresh participants. `known_witness.json` is the final-domain feasibility fixture; `known_witness_report.json` is its independent acceptance record. It is not a baseline, fresh result, or champion.

`calibrate.py` records the earlier exploratory search (seed 2718). Its default family has 87 variables, including occupied-to-virtual hopping and all density interactions; it is **not** the frozen participant domain. `calibration_witness.json` and `calibration_metrics.json` preserve the selected exploratory result. The final instance fixes its occupied/background coefficients, leaving the 42 virtual coefficients unknown. `--locked` records an earlier different fixed-background probe, not a fresh solve of the final task. Exploratory scores are not benchmark scores.

Feasibility was established by privileged calibration before any fresh attempt, followed by independent final-domain validation and a frozen target. No task tuning against a fresh solver outcome is permitted.

Suggested further private search with the unchanged target: optimize the two upper triangles against all 35 scaled triple residuals, a signed-tail target, and admissibility penalties. Use both tail signs, multiple hopping-sign initializations, and continuation toward a 60–150 microEh tail. Bound-constrained least squares with finite differences is tractable; finish with the independent evaluator and comfortable hard-boundary margins. Do not provide these hints or the author fixture to a fresh solver.
