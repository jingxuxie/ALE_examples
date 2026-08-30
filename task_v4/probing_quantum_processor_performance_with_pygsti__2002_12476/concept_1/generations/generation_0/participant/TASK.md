# Robust processor-characterization design

Allocate a limited characterization run for a single-qubit processor whose
coherent errors, decoherence, and readout response vary across operating regimes.
Improve the supplied nominal-design baseline without losing a difficult regime.

`input/candidates.json` contains executable repeated-germ experiments;
`input/contract.json` specifies costs, parameter scales, and limits.
`workspace/physics.py` defines the physical model and the operating-regime
distribution. `input/development.npz` contains representative Fisher features.
`workspace/check.py` scores development designs. `baseline/solve.py` is runnable.

Submit `design.json` in the supplied output directory, with exactly one field
`batches`: one nonnegative integer per candidate. A batch is 64 independent
shots. Limits apply to total execution cost, distinct circuits, and per-circuit
batches. No submitted code is executed by the evaluator.

The score is the fractional reduction, relative to the supplied baseline, of
mean local A-risk for the twelve scaled gate-error parameters after accounting
for two unknown readout parameters. Evaluation uses fresh operating points
from the six disclosed regimes. Pass requires at least **50% overall reduction**
and **40% reduction in every regime**. The evaluator also reports execution
cost and feasibility. These are local information-design scores, not a claim
that an estimator attains a finite-sample Cramer-Rao bound.

Use the one-hour attempt budget and available CPU resources. Python, NumPy,
and SciPy are installed; network access and private evaluator files are absent.
Run the baseline with `python baseline/solve.py --output /OUTPUT/design.json`.
