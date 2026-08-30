# Trusted checker

`trusted_physics.py` is a frozen copy of the public mathematical contract checker. It is outside the participant allowlist and is never imported from a submission. There are no secret correlation targets in this witness task. Hidden tests independently compare tensor contractions against finite-ring state enumeration and compare exact targets against both Cauchy products and Jordan–Wigner finite-size limits.

The final tensor, not submitted code or its claimed observables, is the entire witness. A passing tensor need not be the actual ground state or the energy-optimal MPS: satisfying the stated, independently measurable multiscale approximation properties is the mission.

Contract v3 retains all v2 criteria and adds maximum relative composite-order
covariance error 0.01 over the 60 public quartets. The submitted covariance is
the literal four-X contraction minus the submitted state's two interval means;
the exact target subtracts exact means. No raw-four-point-only gate substitutes
for this covariance condition. All five family scores must equal one.

`test_validation.py` retains the prior independent normalization and contraction
checks. `test_ratchet_2.py` additionally validates every exact composite target,
finite spin ED certificates, independent complex-tensor contractions, own-mean
subtraction, score boundaries, public/trusted parity, malformed archives and
symlink rejection, and the archived baseline. Reports are confined to
`adversary/ratchet_2/`. No passing v3 tensor is known; validation does not assert
feasibility or launch fresh challengers.
