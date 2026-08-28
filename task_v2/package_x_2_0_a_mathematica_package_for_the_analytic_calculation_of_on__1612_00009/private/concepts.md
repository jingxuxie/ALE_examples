# Source inspection and concept triage

The paper PDF and the redistributed, decoded author source are in `sources/`.
The original Hepforge page presents an access challenge. The McMule redistribution
provides the author's source under CC-BY-4.0, including OneLoop.m (6191 lines),
the tensor/Dirac layers, project notebooks, and CollierLink. No licensed Wolfram
runtime is installed. The package's numerical and symbolic internals depend on
Wolfram-private functions; treating a missing proprietary runtime as task hardness
would be invalid. The decoded source is retained privately, not given as a public
answer oracle. No source from the older ALE task is reused.

## Five concepts considered before construction

1. **Weighted-integral release audit and repair (pilot selection; archetype A).**
   Central contributions: weighted four-propagator tensor coefficients, even-
   dimensional continuation, UV/IR separation, and nonsingular multivariate
   expansions. Claim: the combined workflow produces consistent Laurent and
   finite answers at real kinematics, including exceptional Gram geometries.
   Artifact: a benchmark-authored portable reconstruction of the actual
   OneLoop.m stages, rather than pretending the Wolfram source runs in Python.
   Decisions: distinguish analytic singularities from Gram rank loss; select
   direct integration, analytic continuation, or local expansion by regime;
   determine when dimensional factors must be multiplied before subtraction;
   allocate accuracy and work based on convergence evidence.
   Feedback: reproduce precision/order disagreement and trace-identity failure,
   revise numerical/expansion/regularization components, rerun comparisons.
   Public evidence: two tiny exact checks, unlabeled release requests, identities,
   convergence and scale probes. Hidden families include massive weighted
   Euclidean boxes, timelike cuts, UV tensor traces, soft/collinear triangles,
   massless one-mass boxes, and rank-deficient mixed jets.
   Evaluator: continuous coefficient accuracy, minimum-family robustness,
   runtime, and experiment/claim consistency. Likely shortcut: real-simplex
   quadrature plus fixed regulator; this cannot extract IR Laurent coefficients
   or physical cuts. A hybrid remains a plausible successful participant method.
   Construction is contingent on verifying the reference and auditing whether
   the resulting bounded instance still collapses into ordinary implementation.

2. **Light-by-light notebook reproduction with low-energy transfer (B).**
   Contributions: four-point tensors, UV cancellation, Taylor expansion. Real
   artifact: ScatteringLightByLight.nb. Decisions: helicity versus covariant
   assembly, subtraction order, low-energy versus full evaluation. Feedback:
   Ward and Bose identities, energy-scaling runs, precision refinement.
   Public evidence: notebook input cells and invariants. Hidden regimes: heavy
   electron limit, pair threshold, forward scattering. Objectives: amplitude
   accuracy, runtime, cancellation stability. Shortcut: run the complete author
   notebook with a licensed kernel, or copy known helicity formulae. Rejected:
   the proposed regimes are not five independent families; removing the source
   would turn it into reimplementation under an artificial time constraint.

3. **Portable CAS migration of the package (E).**
   Contributions: symbolic tensor reduction, weighted derivatives, arbitrary
   precision. Real artifact: the complete decoded package. Decisions: emulate
   private primitives, rewrite evaluation, retain symbolic precision metadata.
   Feedback: source tests, cross-runtime expressions, numerical comparisons.
   Hidden families: tensor algebra, scalar branches, series. Objectives:
   semantic fidelity, resource use, portability. Shortcut: broad evaluator
   compatibility shims. Rejected: failures are likely interpreter compatibility
   or infrastructure rather than the central research work; public full source
   is also nearly the complete solution.

4. **Singular-threshold expansion beyond regular Taylor (B).**
   Contribution: investigate the documented Landau-singularity limitation of
   LoopRefineSeries. Artifact: series definitions and scalar kernels. Decisions:
   regions versus analytic continuation, matching variable, overlap subtraction.
   Feedback: asymptotic residual slopes, alternative fits, precision reruns.
   Hidden families: soft, potential, collinear regions. Objectives: coefficient
   correctness, asymptotic validity, work. Shortcut: fit a small supplied basis.
   Rejected: a bounded labeled version reduces to fitting; the unrestricted
   alternative exceeds the paper's supported central result and lacks a verified
   general reference in this environment.

5. **Scalar-D0 branch and speed benchmark (A).**
   Contribution: four-point numerical continuation. Artifact: OneLoop.m scalar
   kernels. Decisions: root ordering, continuation convention, precision.
   Feedback: cut signs, permutation invariance, precision sweeps. Hidden
   families: different internal-mass topologies and cut geometries. Objectives:
   error, throughput, worst case. Shortcut: use COLLIER/LoopTools or translate
   the visible author implementation. Rejected: scalar-only outcome is too
   easily one library call, and a finite-only reconstruction is one generic
   contour integration problem. Concept 1 must retain the coupled Laurent,
   weighted-tensor, and multivariate-matching workflow to avoid this shortcut.

## Source locations used for reconstruction

- Paper sections II--V: integration, reduction, D0, and Taylor workflow.
- X/OneLoop.m: scalar continuations approximately lines 1100--2500;
  derivatives and weighted/dimensional reductions approximately 3000--3820;
  UV/IR extraction and tensor reductions thereafter; LoopRefineSeries at 6112.
- X/Documentation/English/Tutorials/ScatteringLightByLight.nb: UV finiteness,
  Ward checks, low-energy matching, and full-kinematics numerical validation.
- X/Documentation/English/ReferencePages/Symbols/LoopRefineSeries.nb,
  PVD.nb, LoopRefine.nb: coefficient conventions and workflow interfaces.

The task does not claim that its Python starter is an official author artifact
or that injected migration errors were reported upstream. The real source is
available for private provenance and independent scientific checks.
