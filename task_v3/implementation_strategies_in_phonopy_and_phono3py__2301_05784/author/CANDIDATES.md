# Candidate ledger — 2026-08-27

The target is arXiv:2301.05784, downloaded as `source/paper.pdf` (23 pages,
including appendices A/B). No separate supplement is advertised on the arXiv
record. The appendices are inspected as supplementary algorithmic material.
All starting wrappers are explicitly author-built capability ablations, not
misrepresented historical checkouts. Solution-bearing official code stays private.
The task descriptions must not name the paper or reveal private references.

## A. Three-origin cubic interpolation (selected: cubic)

- Public starting artifact: a one-origin real-to-reciprocal cubic-force-constant
  interpolator and explicit supercell/primitive mapping inputs, representing v2
  behavior. It does not contain the v3 implementation.
- Private solution: phono3py's `make_r0_average=True` C interaction implementation;
  the v2.9.0 announcement (2023-12-25), v3.0.2 activation (2024-04-21), and v3.23.0
  restoration (2026-01-05) document this exact capability gap.
- Central outcome: origin-consistent reciprocal cubic tensors and phonon-mode
  coupling strengths across noncommensurate wavevectors and unequal bases.
- Shortcut: Fourier-transform one origin, multiply by three, or symmetrize final
  absolute squares. Those operations are not averaging complex amplitudes with
  the proper periodic images before the mode contraction.
- Bottlenecks: primitive/supercell image multiplicities; origin and Cartesian
  permutation covariance; mass/eigenvector contraction and frequency cutoffs.
- Check: stored independent official C outputs, origin/permutation consistency,
  physical material shifts, and runtime for large supercells/triplet batches.

## B. Symmetry-constrained joint force fitting (selected: fitting)

- Public starting artifact: unconstrained harmonic least squares on raw
  displacement-force snapshots, crystal geometry and symmetry actions. No symfc
  package, invariant basis, or reference force constants are visible.
- Private solution: symfc 1.5.4 and official real displacement/force fixtures;
  Seko and Togo, arXiv:2403.03588 / PRB 110, 214302 (2024).
- Central outcome: jointly recover harmonic and cubic constants and predict
  out-of-fit forces while satisfying translational/permutation/crystal symmetry.
- Shortcut: independent rowwise least squares or an unconstrained quadratic fit.
  Sparse noisy snapshots underdetermine the latter, and cubic coefficients scale
  as the cube of atomic count; a generic dense invariant projector is infeasible.
- Bottlenecks: symmetry-adapted parameter reduction; simultaneous polynomial
  orders and acoustic constraints; compact/full indexing; memory-bounded solve.
- Check: official stored force constants and withheld physical force predictions,
  separate order scores, invariance residuals, family minima, runtime and memory.

## C. Generalized Brillouin-zone integration (selected: grid)

- Public starting artifact: orthogonal-grid nearest-component reduction and
  histogram/smearing integration, with a complete array contract.
- Private solution: official BZGrid/SNF, irreducible-grid and linear-tetrahedron
  modules (phono3py 3.19.2 / phonopy 2.43.4); paper sections VI and VII.
- Central outcome: correct BZ boundary images and symmetry-aware integration
  on non-diagonal, anisotropic reciprocal grids.
- Shortcut: round fractional coordinates and replace tetrahedra by a Gaussian.
  Component rounding is not closest-image reduction in an oblique metric, and
  narrow thresholds/flat bands do not converge as a histogram at fixed mesh.
- Bottlenecks: integer grid/coset geometry and boundary ties; spectral integration
  and vertex weights; memory/time at realistic dense mesh size.
- Check: precomputed official geometry and integration outputs, conservation
  checks, skew-grid families, and measured weak-baseline resource behavior.

## D. Coherent transport in complex crystals (not built)

- Public starting artifact: particle-only RTA transport using frequencies,
  linewidths and diagonal velocities.
- Private solution: official Wigner `ConductivityWigner` / velocity-operator code,
  complex-crystal examples, and later inter-band transport implementations.
- Central outcome: population plus coherence thermal conductivity for dense,
  quasi-degenerate optical bands rather than simple-crystal RTA alone.
- Shortcut: add a scalar coherence multiplier to RTA. It cannot recover
  off-diagonal velocity matrix elements or basis-covariant degenerate blocks.
- Bottlenecks: velocity operators/gauge; temperature and linewidth conventions;
  symmetry rotations and tensor aggregation across physical families.
- Check: official Wigner outputs, degenerate-unitary covariance, and RTA limit.
- Selection: not chosen within the four-pilot cap; overlaps polar-mode transport
  more than the selected grid concept. Not declared easy without a pilot.

## E. Temperature-renormalized unstable phonons (not built)

- Public starting artifact: harmonic Gaussian displacement sampling and a fixed
  zero-temperature force-constant model.
- Private solution: official pypolymlp+symfc SSCHA implementation introduced in
  phonopy 2.32.0 (2024-12-05), KCl model and SrTiO3 fixtures.
- Central outcome: self-consistent thermal covariance and stable renormalized
  free-energy curvature where the initial harmonic model is unstable.
- Shortcut: discard imaginary modes or fit independent temperatures. Neither
  solves the sampling-distribution/model mismatch or establishes convergence.
- Bottlenecks: stable stochastic sampling; effective-force regression;
  self-consistency/convergence control and finite-temperature model error.
- Check: expensive precomputed trajectories, withheld forces and free-energy
  stationarity, seed robustness and temperature-family shift.
- Selection: not built because authoring trajectories and converged reference
  uncertainty is costlier than the four available pinned deterministic oracles.

## F. Incompatible harmonic/cubic supercells (not built)

- Public starting artifact: pre-3.0.4 loading/mapping behavior when fc2 and fc3
  use different supercell matrices.
- Private solution: phono3py 3.0.4 (2024-06-07) fix and official separate-supercell
  tests; 3.24.0 (2026-01-07) finite-difference/external-solver integration fix.
- Central outcome: preserve phonons, force-constant ownership and physical
  interactions through mixed-size/mixed-solver loading and serialization.
- Shortcut: reshape or truncate fc2 to fc3 cell. It loses periodic images and
  corrupts compact mapping when primitive-cell conventions differ.
- Bottlenecks: data-schema dispatch; cell/coset mappings; mixed solver semantics.
- Check: round trips, separate-size official fixtures and downstream spectra.
- Selection: exact bug gap, but primarily integration; retained as candidate,
  not rejected as empirically solved.

## G. Isotope-scattering ablation normalization (not built)

- Public starting artifact: pre-c4c54c73 isotope scattering and a three-phonon-only
  conductivity ablation.
- Private solution: phono3py commit c4c54c73 / v2.5.0 (2022-12-29) documented
  overestimation fix; official isotope implementations and examples.
- Central outcome: an isotope/no-isotope ablation that isolates mass disorder
  without corrupting band, degeneracy or tetrahedron normalization.
- Shortcut: global post-hoc rescaling on one material. Error depends on band
  overlaps and integration weights, so it does not transfer to other families.
- Bottlenecks: isotope eigenvector overlaps; spectral integration/normalization;
  separation of scattering channels and conductivity aggregation.
- Check: stored official isotope rates and conductivity differences, isotope-free
  limit and material shifts. No claim that the source published a bad ablation:
  the proposed task checks an ablation invalidated by the documented rate bug.
- Selection: not built within the cap; likely narrower than the selected gaps,
  but no empirical ease claim is made.

## H. Polar dynamical derivatives and mode response (selected: polar)

- Public starting artifact: pre-4.1.0-style fixed-step finite differences and a
  scalar/nondegenerate velocity projection, without the later analytic kernel.
- Private solution: phonopy 4.1.0 (2026-05-25) analytical Gonze–Lee derivative,
  official Python/Rust implementations and polar-material fixtures.
- Central outcome: polar dynamical-matrix derivatives and degenerate-mode
  response, including directional zone-center limits and oblique coordinates.
- Shortcut: use one small finite-difference step and eigenvalue differences.
  It crosses the nonanalytic directional region near Gamma, loses derivative
  information through cancellation, and is not degenerate-subspace covariant.
- Bottlenecks: long-range/short-range differentiation and Cartesian conventions;
  nonanalytic limits; Hermitian degenerate-mode perturbation and scale.
- Check: official analytic tensors, independent finite-difference checks away
  from singularities, stored family-shift outputs and baseline timing.

## Anti-compression decisions (before builds)

The question asked for every pilot is: **Can one fixed general solver handle
every public and hidden case?** A mathematical algorithm can ultimately exist
for each, but no single unadapted dense numerical kernel meets these contracts:

| Pilot | Independent scored components | Required adaptations / scale |
|---|---|---|
| fitting | harmonic fit; cubic fit; symmetry/force predictions | orders, crystal families, compact maps; realistic atom count |
| cubic | image/origin amplitude; phonon-mode coupling | noncommensurate vs boundary points; multi-atom compact cells |
| grid | integer/BZ geometry; tetrahedron spectral measure | skew cells, boundary images, non-diagonal grids; dense mesh |
| polar | full polar derivative; mode-response blocks | polar vs nonpolar, Gamma vicinity, degeneracy, coordinate basis |

The empirical pilots, not this analysis, decide whether a universal shortcut is
actually sufficient. Final acceptance also requires reference >0.90, complete
public contract, fresh score <0.70 and a scientifically substantive residual gap.

## Primary provenance

- https://arxiv.org/abs/2301.05784
- https://github.com/phonopy/phonopy
- https://github.com/phonopy/phono3py
- https://github.com/symfc/symfc
- https://arxiv.org/abs/2403.03588
- https://phonopy.github.io/phono3py/changelog.html
- https://phonopy.github.io/phonopy/changelog.html
- https://phonopy.github.io/phono3py/wigner-solution.html
- https://phonopy.github.io/phonopy/mlp-sscha.html

Exact local revisions, package versions, data hashes and empirical exceptions
are recorded separately during construction and confirmation.
