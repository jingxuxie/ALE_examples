# Partial result

`submission.json` is the best fully certified candidate found during this attempt.
It follows the required four-key artifact format, but **does not meet the requested
population-violation threshold of 0.02**.

The participant's public `api.robust_screen(..., check_paths=True)` recomputed:

- 243 labeled endpoints, with every non-population endpoint gate satisfied.
- All 243 independent continuation certificates, each passing.
- Worst population violation: **0.005577811055211601**.
- Maximum DAD: **0.0009700001828258212**.
- Maximum absolute energy error: **0.00009985001441403796**.

The complete public-oracle report is `validation.json`; its `passed` field is
false because the population target is unmet. This is not a claim that the task
is infeasible. No passing witness was found within this search.

The numerical search scripts, candidate checkpoints, and logs are retained in
this output directory. No participant assets were modified.
