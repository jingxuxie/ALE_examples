# Privileged generation-only achievability portfolio

Date: 2026-08-28. This directory is independent of participant attempts. Only the
frozen `participant/input`, `participant/workspace`, `participant/baseline`, and
`evaluator` content was inspected for this portfolio. No attempts directory was
read, and no task contract, targets, status, or root files were modified.

## Primary sources inspected

- Milsted, Haegeman, Osborne, *Matrix product states and variational methods
  applied to critical quantum field theory*, arXiv:1302.5582v3.
  https://arxiv.org/abs/1302.5582v3
  Uniform MPS optimization, finite-entanglement limitations, and the distinction
  between convergence inside a variational class and accuracy of observables.
- Primary evoMPS repository, snapshot
  `86caa3cdda1e815d96513702b1f50d6fbac471b5`.
  https://github.com/amilsted/evoMPS/tree/86caa3cdda1e815d96513702b1f50d6fbac471b5
  Static inspection of transfer fixed points, pseudo-inverse routines, TDVP,
  tests, and commit history; no evoMPS code is imported by the initial portfolio.
- Correlation-length sorting correction:
  https://github.com/amilsted/evoMPS/commit/add4b7e8720a2ba970fceae236799acb42ab6d11
- Reported density conjugation and stale-cache issues:
  https://github.com/amilsted/evoMPS/issues/22
  https://github.com/amilsted/evoMPS/issues/7
- Stojevic et al., *Conformal data from finite entanglement scaling*.
  https://arxiv.org/abs/1401.7654
  Appendix C shows limitations of central-charge extraction from bond-dimension
  scaling. This portfolio fits literal correlations, not a fitted central charge.
- Vanhecke et al., *A scaling hypothesis for matrix product states*.
  https://arxiv.org/abs/1907.08603
  Transfer-spectrum refinement and the distinction between multiple length
  scales motivate multiscale fitting rather than energy-only optimization.
- Rams et al., *Truncating an exact Matrix Product State for the XY model*.
  https://arxiv.org/abs/1411.2607
  Inspected as a possible construction route; the initial implementation instead
  optimizes explicit finite tensors, with no claim that exact target formulas
  themselves construct a witness.
- Zauner-Stauber et al., *Variational optimization algorithms for uniform matrix
  product states*. https://arxiv.org/abs/1701.07035
- Primary uniform-MPS implementation tutorial:
  https://github.com/leburgel/uniformMpsTutorial
  Inspected as a possible native-solver fallback, not imported initially.
- Haegeman et al., *Unifying time evolution and optimization with matrix product
  states*. https://arxiv.org/abs/1408.5056
- Milsted et al., *Collisions of false-vacuum bubble walls in a quantum spin chain*.
  https://arxiv.org/abs/2012.07243
  Used in the preceding research sidecar to distinguish small-Schmidt numerical
  stiffness from finite-entanglement approximation error.

## Initial construction

`optimize.py` implements independent double-precision, real-valued, parity-block
MPS optimization. Two QR row isometries enforce right canonical form and the
fixed parity convention by construction. The stationary density is obtained by
a differentiable trace-constrained linear solve in the parity-even block space.
Both correlation channels are contracted explicitly at every required distance.
L-BFGS first minimizes energy with progressive bond growth, then optimizes the
three frozen error families together. Checkpoints are scored by the actual
read-only frozen `evaluator/hidden/trusted_physics.py`.

The construction code, run logs, tensor artifacts, and exact checker outputs are
all written under this directory. `derivative_validation.json` records agreement
of the optimization contractions with the frozen checker and a finite-difference
gradient check. A passing state is not presumed: final results must be read from
the saved checker output.

## Completed portfolio

Two independent random initializations, seeds 17 and 71, both produced tensors
accepted by the frozen checker. Seed 17 was selected because its primitive
transfer gap and correlation errors have better margins. The official evaluator
entrypoint and the public checker were subsequently invoked separately on the
copied root `state.npz`; both passed with every family score equal to one.

An additional independent initializer, `imaginary_time.py`, implements a
second-order onsite/inter-site imaginary-time layer, using a bond-two MPO for
the commuting nearest-neighbor XX exponential. Transfer fixed points establish
canonical form, and parity-resolved stationary-density eigenvectors supply
Schmidt compression. This is portfolio-native code, not a copied participant or
upstream solution. It was not needed for the passing artifact.

The energy-only checkpoints and all scored intermediate candidates are retained.
The selected solver logged about 35 seconds, so extending the search to the
optional 30–45 minute budget was unnecessary. `README.md` records the numerical
margins, and `portfolio_results.json` records the artifact hash, exact checker
reports, selected near-miss, and complex-gauge consistency audit.
