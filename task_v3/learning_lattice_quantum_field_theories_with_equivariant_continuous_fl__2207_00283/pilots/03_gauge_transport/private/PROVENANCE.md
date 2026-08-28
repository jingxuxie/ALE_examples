# Provenance and reference independence

This is a compact-group extension gap, not a claim that the original scalar
paper contained an unresolved numerical bug. The original scalar release has
Euclidean continuous flows; the later author library adds Lie derivatives,
Haar-relative density transport and Crouch–Grossmann integration. The public
pilot omits those later modules. Its complete potential is public, so the
challenge is recovering the capability, not guessing an unobserved model.

The private source is `mathisgerdes/bijx` at f476c5b (2026-08-23), archived
under the root `private/sources/bijx`. The corresponding follow-up paper is
arXiv:2410.13161, with the downloaded PDF and data in the source archive.
The source functions actually executed are `lie.value_grad_divergence`,
`cg.crouch_grossmann_step`, `cg.CG3`, and `cg.Matrix`. Generator arrays are
the author's U1_GEN, SU2_GEN and SU3_GEN and are explicitly supplied in every
public/hidden request; their normalization is not hidden trivia.

The loop-potential adapter is authored for this pilot. It is a restricted,
fully specified member of the invariant loop-potential family, rather than
a replica of a released trained gauge network. It uses plaquettes and both
oriented 1-by-2 rectangles, plus trace-polynomial features. A trace-class
potential's linkwise Haar Laplacian equals its single-loop Laplacian summed
once for every distinct link. The source's existing matrix derivative
routine supplies that single-loop Laplacian; no new neural training or
unknown author weight reconstruction is required. `build.py --validate-local`
independently verifies this adapter against an explicit every-link,
every-generator trace of derivatives. The relative discrepancy is recorded
in `reference/local_validation.json`.

The reverse pass differentiates a scan of the author's CG3 stages, rather
than trusting an unrelated approximate gradient. Stored outputs are generated
with 256 steps. `validate.py` compares against 512 steps, and records group
unitarity/determinant residuals. Reference acceptance requires every compared
component score above 0.9. Earlier 64-step checks are development evidence,
not the production oracle. Exact code, seed lists, input arrays, output arrays,
weak-baseline errors and wall times are retained.

Hidden lattices include 16-by-16 fields, matching the follow-up paper's
reported lattice scale. U(1), SU(2), SU(3), forward and inverse time are
independent families. The initial pool uses Haar-random links; the challenge
pool uses valid near-center fields, the sharply concentrated geometry relevant
to compact-group flow densities. Public inputs are two unlabeled 4-by-4
interface examples, not reference-output training pairs.

The generic dense baseline forms the full Hessian in Lie coordinates and
advances sixteen exponential Euler steps. It is run at 16-by-16 SU(3), with
a 240-second timeout and 16-GiB virtual-address guard. Its actual time, peak
resident memory and numerical discrepancy are retained; no quadratic-cost
claim is substituted for a measurement. It is not claimed to represent every
possible optimized automatic-differentiation implementation.

The submitted process sees only the public tree, its own submission, one
current input/output directory, system libraries and the public runtime.
The evaluator uses bwrap with a separate network namespace and preserves
public absolute path aliases. References, case-pool siblings and previous
attempts are never mounted. Submission failures caused by infrastructure are
not considered scientific hardness.
