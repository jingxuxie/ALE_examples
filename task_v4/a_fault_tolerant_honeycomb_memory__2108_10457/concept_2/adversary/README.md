# Validation and adversarial audit

Run `python adversary/test_design.py` from the concept directory. Tests use
only the standard library and do not launch fresh agents. They check the rank
routine against independent elimination and exhaustive error combinations;
all four logical coordinates; malformed, oversized, recursive and duplicate-key
JSON; nofollow rejection of symlinks, FIFOs and special files; fail-closed
asset hashing; public/hidden checker parity; support separation; and the
identity failure versus generator-only construction pass.

`fault_replay.json` records an additional independent Stim audit for every
lattice: 52 explicit single faults, 16 multi-fault combinations, four shots
each, all four logical coordinates exercised, signed logical transport checks,
and deliberate wrong-sign rejections. The signed checks use Stim's signed-flow
API; its documented false-positive bound is 2^-256 per check. The task's GF(2)
correctability computation itself is exact and deterministic.

The circuit generator also proves completeness of the measurement-relation
basis through Stim flow generators, verifies that adding the four reference
correlations raises the relation rank by exactly four, validates steady-state
stabilizer rank `n-2`, and checks noiseless detectors and logical correlations.
It does not inherit the upstream double-EPR annotations or probabilistic test
as a correctness oracle.
