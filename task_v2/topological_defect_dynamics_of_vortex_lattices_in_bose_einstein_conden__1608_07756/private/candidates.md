# Private concept audit

Paper inspected: arXiv:1608.07756v2, all eight pages. Official GPUE repository
snapshot f054145a1d040744e5f57ba2f189494fdb474a66. No downloadable wavefunction
dataset or supplement is linked in the paper/repository. CUDA is unavailable in
this environment. The MATLAB and CUDA source preserves the actual multistage
workflow; a CPU migration is a realistic, bounded reconstruction, not author data.

1. **CPU migration acceptance investigation (selected; archetype A/B).**
   Contribution: phase-only vacancy engineering, subgrid signed-core extraction,
   Delaunay defect analysis and orientational correlations. Claim: erasing a core
   launches sound but need not globally disorder a lattice; larger perturbations
   cannot be diagnosed using density holes alone. Use official source excerpts,
   independently relaxed GPE states, and a benchmark-authored damaged CPU port.
   Decisions: rotation/interaction propagation and stability (unitary splitting
   versus explicit integration); current estimation near singularities (phase
   differences versus complex derivatives); topology in masked finite domains
   (crop-before-triangulation versus guarded component-aware neighborhoods).
   Each has at least two plausible implementations and evidence in invariants,
   control/imprint comparisons and resolution/time-step sweeps. Feedback loop:
   run the port, identify discrepant conservation/order/phonon measurements,
   repair, converge, rerun comparisons. Public evidence: unlabeled initial states,
   a tiny analytic calibration, executable invariant diagnostics, archival code.
   Hidden families: circular rotating bulk; isolated nonrotating condensate;
   rectangular driven elliptic trap; multiply connected annulus; disconnected
   double-well bulk. Evaluate states, signed cores, correlations, energy partition,
   worst family, runtime and evidence consistency. Shortcut risk: textbook split
   step solves propagation, but not the coupled current/topology/evidence pipeline.
   Must reject empirically if a fresh agent repairs the whole workflow easily.

2. **Reanalyse vortex-coordinate trajectories (rejected).**
   Contribution/claim: Delaunay defects and surviving orientational order. Real
   artifacts: MATLAB analysis scripts, no archived coordinates. Decisions: edge
   censoring, tracking, radial bins. Loop: compare order to trajectories. Public
   evidence: geometrical invariants. Families could be disk, annulus, two domains.
   Score geometric correctness/runtime. Shortcut: Delaunay + Hungarian matching
   and proper conjugation almost entirely solves it. Standard coding exercise.

3. **Phase-only robust vacancy control (rejected).**
   Contribution/claim: controlled annihilation and registration sensitivity.
   Artifacts: phaseWinding and paper Fig. 3; no apparatus calibration. Decisions:
   mask bandwidth, registration objective, refinement experiments. Loop: pulse,
   propagate, refine. Families: isolated core, lattice, cluster. Score erasure,
   collateral disorder, mask budget. Shortcut: the opposite atan2 winding is the
   solution without invented hardware restrictions. Adding an SLM would be a
   loosely inspired synthetic inverse problem, not the actual source workflow.

4. **Compressible-energy discrepancy audit (rejected).**
   Contribution/claim: phonon release after phase erasure. Artifacts:
   quKineticSpec.m and observables.py. Decisions: derivative, density cutoff,
   Fourier normalization. Loop: Parseval/partition diagnostics then rerun.
   Families: isolated core, lattice, sound packet. Score spectral accuracy and
   runtime. Shortcut: complex current plus Fourier Helmholtz projection. Alone
   this is a standard algorithm, although valuable inside concept 1.

5. **Recover stationary near-critical lattices (rejected).**
   Contribution/claim: rotating GPE lattice preparation and background order.
   Artifacts: GPE_2d.m, evolution.cu, parameters in paper. Decisions: seeding,
   imaginary-time preconditioner, spatial/time convergence. Loop: optimize,
   inspect energy and cores, refine. Families: circular, elliptic, annular.
   Score energy, stationarity, runtime. Shortcut: seeded normalized gradient
   flow/imaginary-time splitting. Also does not directly exercise the central
   defect-dynamics claim. No second pilot selected merely to exhaust a quota.

The five hidden families in concept 1 differ in physical domain connectivity,
rotation/dynamics, and/or boundary geometry, not just seeds or noise levels.
The common GPE propagator is deliberately insufficient for all scored outcomes:
signed singularities, masked graph neighborhoods, phase-current decomposition,
and physically supported intervention comparisons must agree independently.
