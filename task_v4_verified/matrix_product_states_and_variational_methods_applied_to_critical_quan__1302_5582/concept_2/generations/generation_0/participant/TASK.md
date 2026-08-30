# A critical vacuum in a small tensor

Construct a compact uniform matrix product state for the infinite critical Ising chain, the universality benchmark for critical scalar-field MPS calculations. The state must preserve both local vacuum energetics and long-distance order and density correlations; a low energy alone is not sufficient.

Provided assets: the precise contract and exact target observables in `input/`, a public tensor checker in `workspace/`, and a runnable bond-two baseline in `baseline/`.

Write `state.npz` to your output directory with the complex or real array `A` of shape `(2,D,D)`. The tensor must obey the canonical, symmetry, and primitivity conditions in `input/contract.json`, with even `D <= 24`. All distances and tolerances are public. Run `python workspace/check.py OUTPUT/state.npz` to inspect a candidate.

The witness passes only if all energy, order-correlation and connected-density-correlation tolerances hold. The score also reports the worst observable family. You have one hour of construction time, no network access, and may use the installed CPU numerical libraries. Only the final tensor is evaluated; explanations or claimed metrics are not evidence.
