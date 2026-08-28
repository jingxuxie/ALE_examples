# Private source and concept review

Inspected accepted manuscript and official supplementary notebooks, digitized
inductance data, actual SQUID layouts, scanning simulation scripts, upstream FEM,
solver, current-source, fluxoid and solution modules, and issue history.
Upstream snapshot: 4814482b823c9dba5acaab9e5ba4f85c4d30b0a0.
Supplement snapshot: b8ddc69b9483207ea89adfc1809d79edaf93a405.
The manuscript, notebooks, full source provenance and solution remain private.

## 1. Qualify a reciprocal thin-film device-response pipeline — selected pilot

- Central contribution: arbitrary-geometry London/Maxwell stream-function
  simulation, trapped fluxoids, mutually screening films. Empirical claims:
  ring inductance, reciprocal mutual inductance, and self-consistent SQUID fields.
- Artifact: actual upstream multi-file package and IBM layouts, plus extracted
  meshes and a benchmark-authored qualification adapter. No intentionally
  corrupted upstream code; the adapter's approximations are inadequate under shift.
- Decisions: collocated versus conservative material assembly; point-source,
  softened or integrated near-field interactions; decoupled/fixed-point versus
  globally coupled response; bare-flux versus fluxoid control; reuse versus
  repeated factorization. Evidence: reciprocal response, lift-off sweeps,
  discontinuous material maps, fluxoid-control and driven experiments.
- Feedback: run legacy qualification, inspect reciprocity/field/control failures,
  replace components, compare against ablations and resource measurements.
- Public evidence: complete geometry/material/source definitions, invariants,
  small analytic calibration and a no-label development suite.
- Hidden families: annular inductors; asymmetric perforated washers; real IBM
  multilayer layouts; close shield stacks; patterned films; vortex-bearing slits.
- Objectives: field/current/state fidelity, worst-family transfer, runtime,
  memory, reproducible evidence. Continuous scoring, not pass/fail thresholds.
- Shortcut risk: simply increasing native mesh density/iterations, symmetrizing
  reported inductances, or applying one triangle quadrature correction. These do
  not jointly fix material interfaces, topological control, and mutual screening.
- Not a formula implementation: the existing end-to-end system works in benign
  regimes; its formulation, coupling and readout must be diagnosed and reconciled.

## 2. Transfer scanning susceptometry to experimental scan geometry — reserve

- Contribution/claim: multilayer SQUID imaging and comparison with measured scan.
- Artifact: real 2018-07-25 scan, IBM layouts, row-wise simulation script.
- Decisions: physical sensor geometry versus ideal loop; tilt/registration versus
  penetration depth; background subtraction versus spatially varying material.
- Loop: simulate image, inspect structured residual, revise model and validation.
- Evidence: real scan and supplementary simulated images, calibration metadata.
- Hidden families: different sensor geometries; scan-height/tilt shifts; patterned
  sample response (not independent experimental datasets).
- Objectives: held-out scan fidelity, physical parameter stability, compute cost.
- Shortcut: fit affine registration/height and gain to a cached simulation image.
- Rejected before build: only one usable real experimental scan; could not claim
  five independent hidden data families without synthetic inverse-problem drift.

## 3. Recover mesh-independent vortex fields at very small lift-off — rejected

- Contribution/claim: vortex field and fluxoid agreement with Pearl solution.
- Artifact: official vortex source, field readout, supplementary Pearl experiment.
- Decisions: core model, interpolation, quadrature; loop: lift-off/refinement sweeps.
- Evidence: analytic far-field profiles and flux conservation.
- Families considered: edge vortex, vortex pair, perforated film.
- Objectives: vector-field error, flux conservation, runtime.
- Shortcut: one exact triangle Biot-Savart integration routine solves the core.
- Rejection: too close to a standard numerical integration coding exercise.

## 4. Accelerate inductance sweeps with reusable factorizations — rejected

- Contribution/claim: efficient matrix inversion and mesh-scaling benchmarks.
- Artifact: native factorized model and inductance matrix routines.
- Decisions: caching, precision, direct versus iterative solve; loop: profile,
  optimize and rerun scaling/accuracy measurements.
- Evidence: native tests, runtime profiles and small ring calibration.
- Families considered: rings, multi-hole washers, SQUIDs.
- Objectives: runtime, memory and accuracy.
- Shortcut: batch right-hand sides and call scipy.linalg.lu_solve.
- Rejection: standard library optimization dominates the proposed workflow.

## 5. Topology-aware fluxoid-state design — rejected

- Contribution/claim: quantized trapped flux and inductance-matrix reciprocity.
- Artifact: fluxoid.py, official multi-hole example and inductance pipeline.
- Decisions: integration contours, state objective, coupled versus separate holes;
  loop: compute state, inspect fluxoid errors, refine contour and current control.
- Evidence: fluxoid invariants, reciprocity, a tiny calibrated ring.
- Families considered: nested holes, multiple layers, vortex-bearing films.
- Objectives: fluxoid accuracy, field leakage, current cost.
- Shortcut: native find_fluxoid_solution and one linear solve.
- Rejection: official implementation is already almost a complete solution.

Only concept 1 is authorized for pilot construction at this point. Concept 2
would require a genuinely different source-supported workflow, not more cases
added to concept 1. Source review did not establish such a fallback yet.
