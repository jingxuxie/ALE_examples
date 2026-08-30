# Trusted checker

`trusted_physics.py` is a frozen copy of the public mathematical contract checker. It is outside the participant allowlist and is never imported from a submission. There are no secret correlation targets in this witness task. Hidden tests independently compare tensor contractions against finite-ring state enumeration and compare exact targets against both Cauchy products and Jordan–Wigner finite-size limits.

The final tensor, not submitted code or its claimed observables, is the entire witness. A passing tensor need not be the actual ground state or the energy-optimal MPS: satisfying the stated, independently measurable multiscale approximation properties is the mission.
