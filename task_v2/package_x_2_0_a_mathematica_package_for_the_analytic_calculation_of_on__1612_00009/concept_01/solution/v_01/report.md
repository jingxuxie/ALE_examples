# Release assessment

The inherited sampling pipeline is not reliable. Its scalar geometry cache
aliases weighted and tensor coefficients; its routing permutation does not
carry all parameter insertions; its finite width is not the causal boundary
value; and sampling epsilon at a fixed finite quadrature cannot recover
soft/collinear endpoint poles. The unmodified campaign is in `baseline/`.

The repaired implementation separates analytic Laurent extraction from
finite-parameter integration. Positive-mass requests use covariant parameter
moments, without division by Gram determinants. Timelike requests use a
simplex-preserving deformation with a complete Jacobian. Local multivariate
coefficients are formed inside the regularized representation rather than by
subtracting nearby floating-point answers. UV residues and finite constants
retain the dimensional gamma factors. The supported massless endpoint
topologies use independently derived gamma-function or continued-dilogarithm
representations. The observable assembler multiplies epsilon polynomials
before truncation; replacing d by four prematurely loses finite trace terms.

The production policy refines until successive integrations agree. The `fixed`
ablation uses a single low order with the same continuation. The `direct`
ablation removes continuation and limits refinement, testing whether real
quadrature can support the physical-cut release. The saved tables expose the
resulting coefficient disagreements and work, not merely pass/fail labels.
Figure source data are CSVs. The primary figure's y-axis is disagreement with
production, NOT error against an external oracle; its x-axis is point work.
The second figure shows measured time versus work on logarithmic axes.

Private reference validation additionally compares a changed contour strength
and substantially higher quadrature order, constant-simplex and tadpole exact
answers, the dimensional trace identity, and a closed-form massless triangle.
The public and hidden campaigns agree under independent refinement to better
than 2e-13 relative. The IR box formulas were checked against the decoded author
source including the finite gamma-normalization constants. Internal estimates
alone would not establish those claims. Near physical pinches the numerical
policy can require considerably more work; it is not a claim of uniform cost.

Release is supported for the documented bounded domain. This implementation
does not support power infrared divergences, scaleless UV/IR bookkeeping, all
possible massless box virtualities, complex masses, or expansion at a Landau
singularity. It does not claim arbitrary precision from double-precision
quadrature. Its stability claim concerns the requested coefficients, scale
covariance, and exceptional Gram geometries at the stated accuracy target.
