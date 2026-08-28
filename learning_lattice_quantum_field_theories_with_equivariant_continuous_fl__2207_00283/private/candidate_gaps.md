# Solution-gap inventory

Audit date: 2026-08-28. Original source: arXiv:2207.00283 and
`mathisgerdes/continuous-flow-lft` (paper release e33a0e5; parameter release
e6bec65). Adjacent source: arXiv:2410.13161, its Zenodo 15576712 data,
and `mathisgerdes/bijx` through f476c5b (2026-08-23). Exact source copies
and histories are retained in `sources/`; they are never participant inputs.

## A — Non-unit-time differentiable integration (pilot 01)
- Starting artifact: historical RK4 custom-adjoint implementation, before
  74828bc, embedded in a small composition of density-carrying transforms.
- Private solution: 74828bc and the upstream solver tests; complex-scaling
  correction 7dd214c provides an independently implemented composition check.
- Outcome: accurate primal flow, initial-state/parameter/time cotangents,
  and density bookkeeping for forward and inverse composite transforms.
- Shortcut: replace the adjoint with differentiation through every step.
- Failure regime: long trajectories have a different storage cost; merely
  fixing the primal map cannot repair duration cotangents or density signs.
- Independent bottlenecks: rescaled-time chain rule; complex real-dimensional
  Jacobian; inverse composition and memory behavior.
- Check: stored high-accuracy outputs, finite-difference directional checks,
  actual post-fix implementation, and separate branch scores.

## B — Fourier-space bijections absent from original release (pilot 02)
- Starting artifact: the original real-field representation and a narrow
  spectral-transform API, without the later Fourier metadata implementation.
- Private solution: bijx `fourier.py`, `bijections/fourier.py`,
  `bijections/affine_complex.py` and their independently authored tests.
- Outcome: invertible real/complex spectral transforms with correct real
  degrees of freedom, densities, and derivatives across lattice geometries.
- Shortcut: apply rFFT, multiply a spectrum, and count every stored complex
  coefficient twice.
- Failure regime: mixed parity, Nyquist planes, self-conjugate modes,
  multiple channels, and nontrivial complex phases have different constraints.
- Independent bottlenecks: packing conjugate modes; volume factors;
  physical momenta; channel-aware density composition.
- Check: reference outputs and round-trip/Jacobian identities, including
  realistic lattices for which a dense transform is not viable.

## C — Dense scalar-flow execution at published sizes (pilot 04)
- Starting artifact: released trained parameters and original architecture
  description, but only a weak dense/direct inference implementation.
- Private solution: official Phi4CNF analytic divergence/convolution code,
  later symmetry-aware convolution implementation, and author checkpoints
  from Zenodo 7547918, including the 64-by-64 network.
- Outcome: faithful forward/inverse likelihood evaluation and conditional
  derivatives without reducing the lattice or feature count.
- Shortcut: materialize every translated kernel or a full spatial Jacobian.
- Failure regime: volume-squared work and storage recur at every ODE stage;
  a stochastic trace does not meet deterministic likelihood consistency.
- Independent bottlenecks: factorized trained tensors; exact divergence;
  conditional interpolation; periodic symmetry and scalable execution.
- Check: precomputed outputs from the official implementation, timing and
  symmetry/round-trip probes at the published lattice sizes.

## D — Transfer from scalar fields to compact gauge groups (pilot 03)
- Starting artifact: Euclidean flow interface and explicit gauge-field data
  contracts, with no Lie-group or gauge-vector-field implementation.
- Private solution: the authors' later gauge-flow implementation in bijx,
  its Crouch–Grossmann integrator, Lie differentiation and lattice modules.
- Outcome: gauge-equivariant vector fields, exact Haar-relative divergence,
  manifold-preserving transport and correct sensitivity for U(1), SU(2), SU(3).
- Shortcut: flatten complex matrices into an ordinary ODE and use Euclidean
  traces or finite differences over every coordinate.
- Failure regime: determinant constraints differ between U(1) and SU(N);
  noncommuting stages and tangent divergence cannot be repaired by projecting
  an endpoint; dense Jacobians scale quadratically with lattice volume.
- Independent bottlenecks: oriented Wilson-loop geometry; Lie derivatives;
  Haar divergence; structure-preserving composition and adjoint sensitivities.
- Check: official reference outputs, gauge covariance, group residuals,
  finite-difference checks on small cases and real-size timing cases.

## E — Learned-density discrepancy on released experiment data
- Starting artifact: a limited sample of the actual released gauge/scalar
  experiment diagnostics, unlabeled by quality, and a naive ESS estimator.
- Private solution: the authors' independently generated proposal/target
  density arrays and experiment results, not a newly invented simulator.
- Outcome: reliable support/mode-coverage and uncertainty diagnostics across
  couplings, with claims consistent with withheld independent batches.
- Shortcut: trust proposal-only ESS or fit one Gaussian error bar.
- Failure regime: rare importance weights and mode collapse make apparently
  excellent proposal-side scores coexist with a missing target mode.
- Independent bottlenecks: stable weights; batch dependence; tail coverage;
  separation of bias and statistical uncertainty.
- Check: held-out author batches and independent target-side diagnostics.
- Priority: unbuilt; assess whether the available data really identifies
  missing modes before treating it as a complete task.

## F — Composition of sampler, inverse flow and density conventions
- Starting artifact: pre-fix scaling and continuous-flow components, each
  plausible in isolation, connected to independent Metropolis sampling.
- Private solution: later bijx density fixes, distribution composition,
  sampler implementation and inverse-flow tests.
- Outcome: consistent samples, inverse densities, acceptance ratios and
  parameter sensitivities over mixed real/complex stages.
- Shortcut: fix a sign until one round trip passes.
- Failure regime: round trips can cancel two matching mistakes while
  absolute densities and acceptance statistics remain incorrect.
- Independent bottlenecks: real versus complex volume, reverse ordering,
  stopping gradients, and retained rejected states.
- Check: absolute density and deterministic acceptance traces, not only
  self-consistency. Included as composition pressure in pilot 01.

## G — Symmetry/transfer ablation with an incorrect resize convention
- Starting artifact: pre-555423f convolution resizing, with the original
  scalar experiment's lattice-transfer configuration.
- Private solution: corrected resize implementation and author low/high
  lattice checkpoints, plus symmetry-aware module tests.
- Outcome: transfer retains the intended physical displacement and symmetry;
  the measured gain is not an origin shift or wrong periodic wrap.
- Shortcut: center-pad every kernel identically and compare only one even
  square lattice or only aggregate acceptance.
- Failure regime: odd/even source and target extents and correlation versus
  convolution conventions select different centers and orbit multiplicities.
- Independent bottlenecks: origin convention; orbit sharing; transfer
  normalization; separation of interpolation error from training quality.
- Check: displacement-resolved outputs, equivariance and checkpoint replay.
- Priority: small historical fix alone is unlikely frontier-hard; its
  interaction with scalar execution is assessed in pilot 04.

## H — Exactness versus cost in learned density transport
- Starting artifact: generic auto-Jacobian trace and black-box ODE wrapper.
- Private solution: original closed-form trace architecture and later
  analytic Lie-group divergence/adjoint implementation.
- Outcome: precise likelihoods and gradients within a realistic compute
  envelope rather than merely visually plausible generated fields.
- Shortcut: Hutchinson trace, finite-difference Jacobian, or very small
  steps applied indiscriminately to every family.
- Failure regime: noisy extensive log densities destabilize reweighting;
  full Jacobians and uniform tiny steps multiply cost at realistic volume.
- Independent bottlenecks: geometry-specific exact trace; integration error;
  covariance under symmetry; time/memory allocation.
- Check: likelihood error, gradient error, largest-family runtime and memory
  independently. Represented in pilots 02–04, not a fifth concept.

## Pilot anti-compression decisions

The four concepts are 01 historical differential composition, 02 Fourier
bijections, 03 gauge-family extension, and 04 author-checkpoint scalar
execution. All are built before ranking. A fixed general ODE solver is not
an end-to-end solution: representation, density measure, geometry and
parameter contraction must be independently recovered. For 01, a generic
autodiff replacement remains a credible shortcut and must be tested rather
than ruled out rhetorically. For 02, an FFT is allowed and expected, but does
not specify the independent-mode representation or its density. For 03,
different compact groups change tangent constraints and measure. For 04,
FFT convolution alone does not supply the trained conditional tensor
contraction and trace. No concept is accepted based on this reasoning alone.
