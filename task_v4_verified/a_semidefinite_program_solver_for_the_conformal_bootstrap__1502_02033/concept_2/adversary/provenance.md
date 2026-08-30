# Private primary-source provenance and limits

Inspected on 2026-08-28. This is privileged task generation, not a fresh solving
attempt. No fresh agent is launched by this worker. Only concept_2 is authored.

1. David Simmons-Duffin, *A Semidefinite Program Solver for the Conformal
   Bootstrap*, arXiv:1502.02033v1, submitted 2015-02-06.
   https://arxiv.org/abs/1502.02033
   https://arxiv.org/html/1502.02033v1
   Sections 2.1-2.2 formulate symmetric polynomial-matrix inequalities on an
   entire half-line. Theorem 2.1 gives the positive Gram-matrix translation.
   Matching polynomial identities at finitely many points in that construction
   is not the same as assuming sampled matrix positivity proves continuum PSD.

2. Upstream issue #153, opened 2023-11-21:
   https://github.com/davidsd/sdpb/issues/153
   Reports missed isolated zeros in spectrum extraction. Its example includes
   explicitly isolated constraints outside a continuum block. This motivates
   careful zero handling; it is NOT evidence of an SDPB false PSD certificate.

3. Upstream pull request #274, merged 2025-09-26, not merely an issue:
   https://github.com/davidsd/sdpb/pull/274
   https://api.github.com/repos/davidsd/sdpb/issues/274
   Describes replacing a custom mesh with determinant-polynomial minima via
   MPSolve, and finding isolated zeros. The new input interface also changes.
   Our Chebyshev convolution plus double-precision companion-root heuristic is
   independently authored. It is NOT MPSolve, nor a reproduction of that PR.

4. Upstream issue #285, opened 2025-12-05:
   https://github.com/davidsd/sdpb/issues/285
   https://raw.githubusercontent.com/davidsd/sdpb/4554801/src/spectrum/compute_spectrum/compute_lambda.hxx
   Examines a rank-one assumption in OPE extraction; the cited source takes a
   largest-eigenvalue eigenvector. This motivates checking collective/multiple
   directions, but is not a report about polynomial PSD screening. The task
   intentionally does not reproduce or exploit that indexing/selection choice.

Method caveats: a finite heuristic may have no witness within our bounded
domain. No existence theorem or known successful witness is claimed. Smooth,
well-scaled matrix evaluation does not imply well-conditioned determinant roots
near clustered spectral zeros. The numerical target is deliberately stronger
than any single mesh: multiple independent meshes/profiles, determinant roots
and stationary candidates, adaptive eigenvalue basins, and frozen directions.
All complex roots with eligible real parts are projected; no imaginary-root
filter creates a gratuitous threshold loophole. Noncommutation excludes a
constant eigenbasis but is not a claim of matrix-polynomial irreducibility.
The coordinate-minor restriction enforces collective evidence in the submitted
basis, not in every possible basis. Negative depth is 2,000 times the guard's
absolute tolerance; overflow, NaN, parser and local-code attacks are out of scope
and structurally blocked. Positive controls ensure this is not a reject-all
target. Bounded private sweeps establish only that those attempts failed, never
hardness or impossibility. Fresh-agent classification remains pending.
