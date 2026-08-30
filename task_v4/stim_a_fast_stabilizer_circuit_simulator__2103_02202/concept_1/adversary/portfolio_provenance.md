# Private achievability check

The official fresh result remains `fresh_v_1.json`: mean relative risk reduction
-0.022131548905851044 and worst-family reduction -0.6239256093996475. The
submission returned a structurally valid constant decoder for `biased_0` after
its own inner timeout. This was not a sandbox setup timeout or an evaluator
failure. `outlier_validation.json` independently checks that answer by exact
dynamic programming, characteristic-function scoring, and native Stim sampling.

After grading, generation-time work constructed `safe_portfolio/`. It contains
unmodified copies of the fresh optimizer and its C++ engine, the public baseline,
and a generic controller. The controller saves a baseline answer first, gives
the optimizer a shorter internal deadline, and accepts a candidate only when
its exact worst-regime risk improves on the baseline. There is no case-name
dispatch, private-answer lookup, hidden seed, or hidden-instance data in this
submission. This is a privileged portfolio, not a second fresh-agent result.

`safe_portfolio_evaluation.json` records an isolated run under the unchanged
45-second, one-CPU, 2-GiB conditions and the originally frozen quality target.
All six cases are valid and within resources. Mean reduction is
0.34489023370103783; family reductions are 0.47713973842101914 (biased),
0.10588344291219015 (correlated), and 0.45164751976990414 (drifting).
The portfolio therefore demonstrates achievability.

This narrows the capability diagnosis: the fresh optimizer found strong
solutions on most cases, but failed to preserve safe solution quality across
its full deadline-controlled pipeline. It is not evidence that its underlying
combinatorial search cannot discover good tap sets. Concept 3 supplies the
stronger primary evidence for difficult constructive search.
