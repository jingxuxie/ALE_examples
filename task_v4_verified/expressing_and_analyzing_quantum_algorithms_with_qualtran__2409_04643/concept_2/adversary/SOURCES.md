# Private numerical provenance and scope

Paper seed: arXiv:2409.04643v1, GQSP and Hamiltonian simulation. Official source
snapshot: quantumlib/Qualtran commit 096a2d009059faee0cfae462c3d59cb055300eb9.
The tested route combines fft_qsp.fft_complementary_polynomial with
generalized_qsp.qsp_phase_factors and the native SU2RotationGate convention.
It is deliberately NOT described as the default root-based construction.

The research sidecar considered the complementary-polynomial literature
(arXiv:2406.04246), generalized QSP (arXiv:2308.01501), numerical follow-ups
(arXiv:2505.12615) and upstream numerical issues. Its unarchived exploratory
scores are NOT treated as empirical evidence. Main-session validate.py extracts
the three functions from the actual archived upstream AST, removes only type
dependencies, and checks bit-for-bit numerical agreement with supplied methods.

The evaluator proves contractivity and completion residual bounds over the full
unit circle using exact arithmetic on the submitted binary64 dyadics. It then
checks the circuit independently at 80 digits, with a 120-digit cross-check in
selftests. The error is phase-invariant joint first-column RMS amplitude error.

A degree-96 diagnostic exhibits a large error while its complement is accurate
and no phase guard is entered. Reversing/conjugating the complement produces
near-roundoff reconstruction error, providing a convention/expansion sanity
check. Degree 96 is explicitly OUTSIDE generation 1's 32–48 range and does not
prove that generation achievable. The task's dense degree range, contraction margin,
six configurations and guard exclusions prevent simply replaying that failure.
Unless a complete admissible in-domain witness is checked, solvability remains
unknown and a failed fresh search can only support hard_open_candidate.

Generation 1 later acquired valid degree-48 witnesses; generation 2 acquired
valid degree-14 witnesses. Generation 3 restricts the degree to 8–12. Neither
historical witness proves solvability in this final domain. The private ratchet
notes and per-generation archived evaluators distinguish these claims explicitly.
