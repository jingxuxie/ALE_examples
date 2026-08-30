# Resilient processor-characterization design

Improve a strong characterization design so that it remains informative when
measurement records for any two selected circuits are lost. Preserve ordinary
characterization efficiency and the original hardware budget.

`input/candidates.json`, `input/contract.json`, and `workspace/physics.py` define
the single-qubit processor, six operating regimes, candidate experiments, and
costs. `input/development.npz` supplies representative Fisher features.
`baseline/design.json` is the current champion; `baseline/solve.py` emits it.
`workspace/check.py` scores a proposed design on development operating points.

Submit a static `design.json` in the supplied output directory, with exactly
one field `batches`: one nonnegative integer per candidate. Each batch is 64
shots. Respect the total execution budget, at most 24 distinct circuits, and
the per-circuit batch cap. All allocated costs are paid even when data are lost;
there is no adaptive reallocation. Symlinks are not submissions.

For each operating point, loss-risk is the largest local A-risk after removing
all batches from any set of up to **two** selected circuits. Readout parameters
remain unknown nuisance parameters. Score the mean loss-risk reduction against
the supplied champion, with fresh operating points from the disclosed regimes.
Pass requires **50% overall reduction**, **30% reduction in every regime**, and
intact mean A-risk no more than **1.20 times** the champion's intact mean A-risk.
The score is a local information-design objective, not a finite-shot estimator
guarantee. Execution cost, feasibility, and each regime are reported separately.

Use the one-hour attempt budget and available CPU resources. Python, NumPy,
and SciPy are installed; network and private evaluator access are absent.
Example: `python baseline/solve.py --output /OUTPUT/design.json`.
