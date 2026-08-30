# First champion ratchet

Generation 1 was solved by the isolated ultima-alpha attempt. Its exact degree-4
witness has a common null vector. The full determinant vanishes identically;
sampled smallest eigenvalues have a flat zero branch, and a separate quartic
basin attracts the limited secondary-eigenvector probes. This is a genuine
semidefinite boundary failure, not malformed input or an overflow.

The private challenge space contains 168 admissible cases: 24 signed coordinate
permutations at each of seven trace-preserving positive lifts of the null mode.
All preserve the exact collective negative witness and required entry/minor
constraints. The old method falsely accepts 24 cases, and the proposed method
accepts none. Exact common-nullspace checks establish the root-cause cluster.

Generation 2 replaces full-determinant-only candidates with candidates from all
principal minors. Other screening stages, coefficient bounds, exact negativity
thresholds, and resource conditions are unchanged. The new method remains a
floating-point heuristic, not an exact real-root or PSD certificate. No passing
generation-2 witness is known at publication. The old winning artifact and full
prior packet are private; no previous submission is given to the next agent.
