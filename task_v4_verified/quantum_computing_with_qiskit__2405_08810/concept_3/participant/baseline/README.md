# Fixed-schedule baseline

`solution.py` is runnable through `../input/local_simulator.py` or the official evaluator. Its 192 queries each receive 128 shots: 16 zero-time signed single/parity calibration settings and 16 conditional/control-coherence settings at each of 11 fixed nonuniform durations. No experiment depends on observed outcomes.

It fits all nine parameters jointly using SciPy bounded `least_squares` with an arcsine variance-stabilized binomial residual. Twelve deterministic multistarts fit the short-time prefix, and up to three candidates are refined on the full data. A wall-clock guard leaves time to report the estimate. The public model supplies exact probabilities; it does not approximate noncommuting evolution by a product of Pauli rotations.

The public development run (`--seed 7241 --episodes 4`, one episode per family) measured mean NRMSE **0.08660264**, with family errors **0.04522463**, **0.09847692**, **0.05580656**, **0.14690247** in the published family order. All four episodes were valid and used the full budget. The run took **11.26 seconds total**, with maximum episode wall time **3.41 seconds** on the builder's trusted local harness. These are a small development sample, not an accuracy guarantee on the hidden suite. Subsequent timing-only safeguards move the fit timer before imports, reserve response time, and distribute the one-core affinity; the normal full fitting schedule is unchanged.

The frozen pass target is mean NRMSE **≤0.060** and worst-family mean NRMSE **≤0.090**, with **32/32 valid episodes**. The full frozen-suite baseline measured **0.07761136 mean NRMSE**, **0.11498585 worst-family NRMSE**, and **32/32 valid episodes**, with resource compliance **1.0**. Thus the targets require approximately **22.7% lower overall error and 21.7% lower worst-family error** than this baseline. The baseline does not pass.

| Family | Mean NRMSE |
| --- | ---: |
| aliasing | 0.10164491 |
| near_degenerate | 0.04486595 |
| weak_entangling | 0.04894873 |
| nuisance_decoherence | 0.11498585 |

The startup-aware sandboxed run took **341.89 seconds total**, of which **58.82 seconds** were solver time and **283.07 seconds** sandbox startup. The maximum episode solver time was **5.53 seconds**. Summary data are in `metrics.json`. No hidden parameter, episode estimate, or seed is published.

All 32 frozen episodes have full rank nine for the nuisance-inclusive probability Jacobian under the fixed schedule. A true-parameter local Fisher allocation diagnostic respecting the same budgets gives mean RMS bounds of **0.04187** overall and **0.06194** in the worst family. This suggests useful design headroom, but is neither a submitted controller, a finite-sample guarantee, nor a proof that the target is achievable. The target remains open.
