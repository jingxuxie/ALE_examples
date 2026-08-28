# Source-gap inventory and pre-pilot decisions

Target: arXiv:1310.6143. Authoring began 2026-08-27 (America/Los_Angeles).
The source is a methods review, not an unsolved problem statement. All candidates
below therefore separate the older capability from a later privileged artifact.
No difficulty judgment below substitutes for the empirical tournament.

## A — Parallel spin-accumulation repair
- Starting artifact: official VAMPIRE parent of `ed2f0719`, with serial transport.
- Private artifact: `ed2f0719` ("Fix parallel computation of spin accumulation").
- Outcome: decomposition-invariant accumulation, currents, and atomic torques.
- Shortcut: execute only the serial path or sum already-normalized local vectors.
- Failure regime: split cells, unequal ownership, empty ranks, and nonuniform moments.
- Independent bottlenecks: extensive/intensive reductions; atom-to-cell mapping;
  transport-to-torque normalization.
- Check: cross-decomposition comparisons to the fixed official implementation,
  current continuity, and torque sum rules.

## B — Non-Markovian quantum thermostat (selected: quantum_bath)
- Starting artifact: white-noise, local-damping spin dynamics without the later
  quantum module; executable reduced classical baseline.
- Private artifact: official `origin/quantum-thermostat`, the 2025 follow-up
  arXiv:2508.11315, and author archive doi:10.5281/zenodo.18391022.
- Outcome: calibrated bath spectra and coupled spin/memory transients across
  classical, quantum, and zero-point-subtracted baths.
- Shortcut: temperature-rescaled white noise, or independently colored noise
  added to an unchanged Gilbert integrator.
- Failure regime: resonant short-time dynamics, low temperature, and mixed moments.
- Independent bottlenecks: spectral normalization/statistics; causal dissipative
  memory; intermediate-stage exchange coupling; bounded storage.
- Check: stored later-method outputs, covariance/spectral checks, trajectory
  convergence and independent fluctuation-dissipation consistency checks.

## C — Large irregular dipolar systems
- Starting artifact: original point-macrocell demagnetization implementation.
- Private artifact: official hierarchical branch and Jenkins/Evans 2020 archive
  doi:10.5281/zenodo.3669966; corrected near-cell tensor construction.
- Outcome: accurate dipolar fields and time-dependent updates at device scale.
- Shortcut: dense pairwise tensors or one regular-grid FFT.
- Failure regime: irregular occupied cells, atomistically resolved near fields,
  and micrometre-scale memory use.
- Independent bottlenecks: geometry-aware near tensors; spatial hierarchy;
  temporal refresh decisions.
- Check: stored direct sampled-target fields, tensor reciprocity, independently
  converged hierarchical results and measured memory/time.
- Not built: a field-only reduction risks violating the no-universal-kernel rule;
  a complete space/time device benchmark needs longer authoring than the four
  selected integration-oriented pilots. This is not a prediction of agent success.

## D — Nonuniform transition mechanisms (selected: activation)
- Starting artifact: energy/gradient and ordinary local spin relaxation only.
- Private artifact: Spirit GNEB, minimum-mode following and HTST, adjacent
  arXiv:1901.11350 and its official implementation.
- Outcome: physically valid transition saddle, activation barrier, and entropic
  lifetime factor for nonuniform spin textures.
- Shortcut: coherent rotation or linear interpolation between relaxed endpoints.
- Failure regime: domain-wall nucleation, collapse versus escape and soft modes.
- Independent bottlenecks: manifold saddle/path optimization; saddle-index
  certification; tangent-space fluctuation determinants and dynamics.
- Check: private converged saddle/barrier/prefactor outputs, residual torques,
  normalization and Hessian inertia.

## E — Classical-model discrepancy on measured magnetization
- Starting artifact: original classical Ni/Gd material parameters and sparse
  measured temperature-dependent magnetization/phonon DOS observations.
- Private artifact: follow-up author data at doi:10.5281/zenodo.18391022 and
  quantum-thermostat simulations reproducing measured Ni and Gd curves.
- Outcome: cross-temperature prediction without re-fitting each observation.
- Shortcut: a scalar temperature rescaling or generic interpolation of labels.
- Failure regime: changing bath spectrum, zero-point treatment, and short-time
  response outside a fitted equilibrium curve.
- Independent bottlenecks: DOS calibration; statistical model choice; transfer
  from equilibrium to dynamical observations.
- Check: held-out experimental data and stored author transients, with data
  uncertainty rather than artificially exact labels.
- Not built separately: would overlap B; preserve it as a distinct scientific
  direction and potential source-grounded diagnostic, not an extra pilot.

## F — Multisublattice spin transport (selected: transport)
- Starting artifact: pre-sublattice transport state `f415696e`/its parent and
  non-sublattice baseline, with geometry and material inputs retained.
- Private artifact: official `ea671c16`, `b1afc4f7`, `7870918f`, `e3c8ab8d`
  sequence, including removal of empty-sublattice electrical shorts.
- Outcome: finite multilayer resistance, resolved currents and consistent
  atomistic torque under noncollinear magnetic order.
- Shortcut: average magnetization before transport or give absent channels zero
  resistance; use a scalar resistor network without torque back-coupling.
- Failure regime: compensated antiferromagnets, partially occupied sublattices,
  reversed current, and interface mixing.
- Independent bottlenecks: channel topology/occupancy; spin-resolved transport;
  physical torque projection and normalization.
- Check: official post-fix outputs, continuity, empty-channel limits, polarity
  and sublattice permutation symmetries.

## G — Finite-temperature anisotropy ablation (selected: free_energy)
- Starting artifact: unconstrained equilibrium sampler and zero-temperature
  energy-difference baseline, without constrained sampling/free-energy logic.
- Private artifact: official constrained/hybrid Monte Carlo implementation and
  adjacent arXiv:1006.3507 plus official anisotropy workshop input decks.
- Outcome: anisotropy free-energy/torque curves for competing bulk, surface and
  material-resolved terms, separating internal energy from free energy.
- Shortcut: zero-temperature energy scaling with a universal magnetization power.
- Failure regime: competing anisotropies, elevated temperature, interfaces and
  noncollinear order where entropy changes the inferred barrier.
- Independent bottlenecks: constraint-preserving detailed balance; mixing and
  uncertainty; angular thermodynamic integration/material constraints.
- Check: converged private Monte Carlo torque references, statistical error bars,
  angular symmetries, and thermodynamic integration consistency.

## H — Atomistic FFT correctness/performance tradeoff
- Starting artifact: pre-FFT or early FFT branch around `3f9bc70d`.
- Private artifact: `3f9bc70d` FFT implementation plus `8e5417ff` self-term fix,
  `31bb4692` follow-up and `8316e9fd` precision-related tensor repair.
- Outcome: correct atomistic fields with acceptable memory and precision.
- Shortcut: periodic convolution used for open boundaries, or silently substitute
  coarse macrocells and omit on-site terms.
- Failure regime: surfaces, compensated multi-atom cells and mixed precision.
- Independent bottlenecks: boundary embedding; tensor/self-term conventions;
  precision stability and atomistic-to-cell mapping.
- Check: direct small-system oracle, stored large-system references and precision
  convergence. Not built separately because of overlap with C.

## Anti-compression gate for the four selected pilots

| Concept | Could one fixed generic numerical kernel suffice? | Required independent work |
|---|---|---|
| quantum_bath | No: an ODE solver does not infer/generate the correct bath statistics. | Bath spectrum + causal memory/exchange dynamics + storage |
| activation | No: a local minimizer neither finds index-one saddles nor fluctuation determinants. | Mechanism/saddle search + constrained Hessian/prefactor |
| transport | No: a linear solver does not define channel topology or physical atomic torques. | Occupancy/topology + resolved transport + torque mapping |
| free_energy | No: energy minimization does not compute constrained thermal free energies. | Detailed-balance sampler + mixing/error control + integration |

These are provisional gates. If empirical attempts expose a universal shortcut,
the tournament must record it and reject or naturally ratchet the concept.

## Primary source locators

- https://arxiv.org/abs/1310.6143
- https://github.com/richard-evans/vampire
- https://github.com/richard-evans/vampire/tree/quantum-thermostat
- https://arxiv.org/abs/2508.11315
- https://zenodo.org/records/18391022
- https://zenodo.org/records/3669966
- https://github.com/spirit-code/spirit
- https://arxiv.org/abs/1901.11350
- https://arxiv.org/abs/1006.3507
- https://vampire.york.ac.uk/resources/workshop2017_day2.pdf

Exact source revisions, executable reference coverage and any deviations from
these provisional pilot scopes are recorded by each build and in the final report.

## Empirical correction to the provisional gate

All four initial fresh attempts solved their frozen initial scopes. The table's
initial "No" answers distinguished a single numerical kernel from a composite
solver; they did not establish that a fixed composite solver would fail. In
fact the attempts constructed reusable composite solvers: channel algebra,
FFT forcing plus adaptive integration, manifold saddle search plus fluctuation
analysis, and constrained sampling plus angular reweighting. The private source
gaps were real, but those gaps alone did not establish frontier difficulty.

Transport and quantum bath also solve every case in their pre-generated private
challenge pools. They are discarded rather than rescued by unrelated physics,
arbitrary tighter tolerances, or ill-conditioned long-time trajectory matching.
Activation and thermal free energy have the lowest initial worst-family scores
and are retained only for source-grounded counterexample review. A long-chain
activation timeout is documented separately; it is not retroactively counted
as an initial-scope failure, and a pure one-kernel optimization would not by
itself establish an acceptable hard task.
