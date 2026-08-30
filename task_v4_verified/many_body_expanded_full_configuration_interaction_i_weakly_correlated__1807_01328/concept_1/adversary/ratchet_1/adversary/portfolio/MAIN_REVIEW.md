# Independent achievability review

The main session independently reran `candidate_a` against the unchanged E2
evaluator in its feature-only bubblewrap namespace. The result in
`main_independent_score.json` is valid and passing: overall RMSE
7.801096598563731e-6 Eh, worst-stratum RMSE 1.4833026647628145e-5 Eh, maximum
query cost 160, aggregate CPU 61.39958 seconds, wall 85.95023 seconds, and peak
policy RSS 70,500,352 bytes. The accuracy matches the original portfolio run
exactly. All E2 constraints remain unchanged.

Static review compares the candidate with the archived generation-1 champion.
The neural-weight files are byte-identical to that previous fresh submission,
which was trained with public assets inside its original isolation boundary.
The acquisition implementation is also unchanged. The added policy code
computes a low-triple-activity diagnostic and a covariance from observed
single/pair/triple increments, changes its query choice, and conditionally
bypasses a physical correction. It contains no private Hamiltonian coefficients,
case identifiers, hidden-label tables, or runtime access to generation data.
The evaluator mounts no such data into the policy process.

The portfolio's separate 120-case holdout passes with overall RMSE
6.206213746538193e-6 Eh and worst-stratum RMSE 1.1397722136980909e-5 Eh. It was
not used for tuning. Its conditioned cases remain in two seed-derived
neighborhoods, so this is not a guarantee over the entire enclosing parameter
domain. Achievability of the actual fixed E2 benchmark is nevertheless
demonstrated by a runnable, observation-driven, resource-valid policy.

At the time of the initial achievability review, the fresh E2 attempt was still
running with no access to this policy or any prior private artifact. It
subsequently fails the unchanged target with valid protocol/resources:
18.1089 microEh overall and 31.7704 microEh worst-stratum RMSE. Main's independent
replay again fails at 18.1165/31.7704 microEh. The final E2 disposition is
`hard_verified_achievable`, scoped to these isolated one-hour attempts and this
fixed benchmark, not a general hardness proof.
