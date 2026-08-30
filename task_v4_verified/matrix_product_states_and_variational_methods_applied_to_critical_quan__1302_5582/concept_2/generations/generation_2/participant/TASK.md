# A critical vacuum in a small tensor

Construct a compact uniform matrix product state for the infinite critical Ising chain, the universality benchmark for critical scalar-field MPS calculations. Preserve local vacuum energetics, all specified two-point channels, and the connected fluctuations of two separated order-operator pairs. Low energy or accurate raw four-spin correlations alone is not sufficient.

Provided assets: the precise contract, exact observable definitions and all 60 four-site geometries in `input/`, a public tensor checker and exact-observable helpers in `workspace/`, and a previously optimized bond-24 tensor in `baseline/state.npz`. No previous construction code is provided.

Write `state.npz` to your output directory with the complex or real array `A` of shape `(2,D,D)`. The tensor must obey the canonical, symmetry, and primitivity conditions in `input/contract.json`, with even `D <= 24`. All distances and tolerances are public. Run `python workspace/check.py OUTPUT/state.npz` to inspect a candidate.

The witness passes only if all energy, order, connected-density, y-spin and composite-order covariance tolerances hold. In particular, the maximum relative composite-covariance error must be at most 0.01 over all 60 listed quartets. The submitted covariance subtracts the submitted state's own two interval means; its exact target subtracts the corresponding exact means. This requirement measures accurate operator-product fluctuations, not just raw four-point agreement. The score also reports the worst observable family.

You have one hour of construction time, no network access, and may use the installed CPU numerical libraries. The evaluator has a 120-second timeout. Only the final regular-file tensor artifact is evaluated; symlinks, explanations or claimed metrics are not evidence. The provided baseline does not pass this contract; no passing tensor or feasibility guarantee is supplied.
