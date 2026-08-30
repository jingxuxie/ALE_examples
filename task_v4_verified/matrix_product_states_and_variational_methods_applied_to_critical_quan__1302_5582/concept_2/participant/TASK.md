# A critical vacuum in a small tensor

Construct a compact uniform matrix product state for the infinite critical Ising chain, the universality benchmark for critical scalar-field MPS calculations. Preserve vacuum energetics, the specified two-point channels, and connected fluctuations of two and three separated order-operator pairs. Low energy or accurate raw moments alone is not sufficient.

Provided assets: the contract, exact observable definitions, all 60 quartets and 252 sextuples in `input/`; a public checker and exact-observable helpers in `workspace/`; and a previously optimized bond-24 tensor in `baseline/state.npz`. No previous construction code is provided.

Write `state.npz` to your output directory with the complex or real array `A` of shape `(2,D,D)`. The tensor must obey the canonical, symmetry, and primitivity conditions in `input/contract.json`, with even `D <= 24`. All distances and tolerances are public. Run `python workspace/check.py OUTPUT/state.npz` to inspect a candidate.

All six families must pass: energy, order, connected density, y-spin, two-interval covariance (at most 1% relative error on every quartet), and the connected three-interval cumulant K3 (at most 10% on every sextuple). Definitions are in `input/observables.md` and `input/three_interval_cumulant.md`. Submitted connected quantities use the submitted state's own means and lower moments; exact targets use exact means and lower moments. The score also reports the worst family.

You have one hour of construction time, no network access, and may use the installed CPU numerical libraries. The evaluator has a 120-second timeout. Only the final regular-file tensor artifact is evaluated; symlinks, explanations or claimed metrics are not evidence. The provided baseline does not pass this contract; no passing tensor or feasibility guarantee is supplied.
