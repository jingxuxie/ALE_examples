# Private provenance and scientific limits

Inspected 2026-08-28. Primary sources:

- https://arxiv.org/abs/1504.07997 and https://arxiv.org/html/1504.07997v2
  (Kos, Poland, Simmons-Duffin, Vichi; submitted 2015-04-29, v2 2015-06-22).
  Section 2 writes the singlet contribution as an OPE-vector quadratic form;
  the singlet functional positivity condition is a 2x2 PSD matrix constraint.
- https://github.com/davidsd/sdpb/issues/153 (opened 2023-11-21).
  The reported missing zero is a saturated *isolated point constraint*, not
  evidence that all continuum tangencies are missed. This task includes both
  point constraints and continuum tangencies and distinguishes them explicitly.
- https://github.com/davidsd/sdpb/pull/274 and the GitHub REST pull endpoint.
  Title: spectrum: new interface and zero-finding algorithm. Merged
  2025-09-26T19:32:21Z; merge c39fd50686b1cc02851864cd5799c24daf20ea68.
  It changes the spectrum interface and uses MPSolve on determinant minima;
  it also handles isolated zeros. No upstream implementation was copied.
- https://github.com/davidsd/sdpb/releases corroborates the rewrite in 3.1.0.

The new task uses the same complementarity idea, M(x) u = 0, but neither its
polynomials nor its global linear measurements are actual 3D crossing blocks.
An atomic PSD measure has residues w uu^T, so a unit-trace projector and positive
weight have a consistent reduced OPE interpretation. M alone cannot determine
w; explicit independent matrix-polynomial measurements supply that information.
Rank-two zeros and degenerate decompositions are excluded rather than assigning
scientifically unjustified individual OPE vectors to them.

## Construction and exhaustive witnesses

The private generator does exact rational polynomial arithmetic. Each continuum
M is a positive scalar times C(t)^T diag(d0(t), d1(t)) C(t). C is a polynomial
rotation [[1,a],[-a,1]], an invertible constant congruence, and a unit-determinant
polynomial shear; det(C) = 1.164*(1+a(t)^2), strictly positive on the real line.
Each d is an even power of a rational symmetric irreducible tridiagonal matrix's
characteristic polynomial, times a strictly positive quadratic, optionally
times 1+t or 1-t. Thus the witnesses list ALL and ONLY domain zeros. Algebraic
roots come independently from 290-digit symmetric-matrix eigensolutions, not
from the participant's root finder. Every tridiagonal off-diagonal is nonzero,
giving simple eigenvalues. Checks exclude coincident branches and rank-two zeros.
Matrices are converted to Chebyshev coefficients *exactly* and serialized as
terminating decimals. The moment RHS is rounded only at 240 significant digits.
This is not cancellation induced by first rounding generated data to binary64.

All known positions, projectors, weights, seeds, certificates and case-family
identities remain private. Public samples are independent seeds, input-only.
The evaluator does not import the generator: it uses assignment to stored
witnesses plus a separately implemented Clenshaw evaluator for matrix-null and
global moment residuals. Acceptance tolerances and thresholds are fixed in TASK.

## Shortcut analysis

For a rational PSD polynomial determinant, exact square-free/GCD processing is a
natural and permitted strategy. This construction does not pretend that hiding
the factorization prevents that. Rational factorization can expose characteristic
polynomials; eigenvalues are generally algebraic rather than a list of planted
rational linear factors. Positive quadratics introduce nearby complex roots;
point blocks need independent treatment and endpoints need domain filtering.
Even perfect determinant roots provide at most 0.30 of the score without correct
null projectors. Correct roots and projectors with incorrect weights provide at
most 0.70, below the fixed 0.90 threshold. Multiscale amplitudes, sub-grid clusters,
rapidly moving nulls, and the high-precision coupled moment inversion remain.
A robust exact-isolation + high-precision geometry + equilibrated linear solve
is an intended strong approach, not an exploit. No restriction on legitimate
root algorithms is used to manufacture difficulty. SymPy is not a guaranteed
participant dependency; an optional organizer-only factorization audit uses it
when installed. No assertion is made that exact algebra is necessarily slow.

## Evidence classification

Validation records are in this private tree. Known-witness scoring demonstrates
that the answers satisfy the objective, **not** input-only spectrum discovery.
Witness-coordinate-conditioned moment reconstruction checks that weights are
identifiable from public measurements. Neither is a tournament reference solver.
No full input-only high-performance reference or fresh-agent tournament is
claimed. The main user must perform the independent improvement tournament.
