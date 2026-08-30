# Empirical hardness report

Scores are core / worst-family. Fleet scores are percentage loss reductions; pulse and spectroscopy scores are in [0,1].

## Concepts and scores

### A — Adaptive symmetry diagnostic fleet
- Baseline: 0% / 0%; repaired fixed target: 2.5% / 1%.
- Both fresh attempts and the champion: 4.809922% / 2.586467%.
- Final status: `solved`; solvability demonstrated. The original 6% / 3% contract was invalidated, not retained as hard.

### C — Calibration-aware coherent many-body pulse compilation
- Weak baseline: 0.014322 / 0.000000.
- Private passing witness: 1.000000 / 1.000000; fixed target: 0.999995 / 0.999990, with minimum-column fidelity at least 0.999990.
- Fresh v1: 0.239150 / 0.118793; fresh v2: 0.262706 / 0.066015. Both artifacts satisfy hardware constraints but fail accuracy.
- Final status: `hard_verified_achievable`; solvability demonstrated by the private witness.

### E — Shot-budgeted active spin spectroscopy
- Original baseline: 0.949463 / 0.934595; ratchet champion-baseline: 0.962765 / 0.948940.
- Initial fresh v1: 0.987571 / 0.986181; initial fresh v2: 0.988716 / 0.985711.
- Ratchet fresh attempt / current champion: 0.985402 / 0.984954; fixed target: 0.970000 / 0.950000.
- Final status: `solved`; solvability demonstrated.

## Counterexample searches

- Fleet: a guarded relaxation disproves the original 6% / 3% target. After repair, 12 private stress fleets and two equivalent-order variants produce no substantiated champion failure; relaxation gaps alone are not treated as feasible improvements.
- Pulse: 49 saved numeric pulse artifacts produce no valid witness. The checker rejects 17 invalid-artifact cases, independently validated propagation agrees, and the private positive witness passes.
- Spectroscopy: a 48-case private stress space exposes the initial champion at three configurations while total shots remain fixed. A fresh agent solves that ratchet; the new champion also passes the prospective two-configuration audit.

## Ratchets and final decision

- Champion-ratchet generations: fleet 0; pulse 0; spectroscopy 1. Fleet also has one separate contract-repair generation.
- Seven isolated `ultima-alpha` attempts, each limited to one hour, are complete and scored.
- Retained task: `concept_2/participant/TASK.md`. Final status: `hard_verified_achievable`. Solvability is demonstrated, not unknown.
- Substantive failed capability: Joint inverse synthesis of a hardware-constrained, 72-parameter noncommuting many-body pulse reproducing coherent six-state register isometries across four fully disclosed calibrated Hamiltonians.
