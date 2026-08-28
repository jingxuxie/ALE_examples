# Private concept triage

Source: arXiv:2103.02403v2, its 2024 erratum, and qutech/filter_functions
commit 5f8175f3998f9bfab085cac9946e7796595082e3. Real artifacts include
examples/data/{X2ID,Y2ID,CNOT}.mat, examples/qft.py, randomized_benchmarking.py,
and tests/testutil.py. The shipped numerical package is extracted from v1.2.1,
before the real second-order integral limiting-case repair f24933c.
The task does not disclose the paper or the erratum.

## 1. Process-prediction release audit (selected; archetype A/B)
- Contribution: generalized sequence filter functions, coherent error shifts,
  and preservation of inter-gate noise memory. Claim: accurate and efficient
  process/fidelity prediction; experimentally investigate its domain of validity.
- Assets: real optimized spin-qubit pulses and the official multi-file package;
  benchmark integration code and explicitly authored transfer experiments.
- Decisions: integration/coherent-term error versus model truncation;
  averaging with shared memory versus independently composing channels;
  perturbative spectral prediction versus deterministic/stochastic ensemble
  propagation, selected against accuracy, convergence, and runtime evidence.
- Loop: reproduce diagnostic disagreement, isolate representation/numerical/model
  causes with noise-strength and segmentation ablations, repair, rerun and certify.
- Public evidence: small commuting exact calibration, physical invariants,
  noisy low-sample trajectory diagnostics, real controls, unlabeled transfer cases.
- Hidden families: quasistatic Gaussian driven gates; finite-memory Gaussian OU;
  non-Gaussian switching; white noise; weak broadband multi-qubit control;
  physical six-state leakage. Different process laws and computational regimes.
- Evaluation: full channel and quadratic generator accuracy; worst family;
  actual runtime and memory; evidence and claims independently recomputed.
- Shortcut risk: `error_transfer_matrix(second_order=True)` fixes only one
  approximation. Monte Carlo is general but cannot deliver low-error weak-noise
  channels cheaply; one hierarchy is not efficient for arbitrary broadband spectra
  in the six-state real pulse workflow. Empirical screening decides, not this claim.
- Not a direct translation: the task gives the stochastic Hamiltonian and an
  incident, not a solution recipe. Numerical correctness, model adequacy, and
  scientific evidence must be separated and reconciled.

## 2. Conditional syndrome-memory prediction (reserve; archetype E)
- Contribution: concatenated correlated-noise processes; test when endpoint
  channel composition ceases to predict measurement-conditioned histories.
- Assets: official control/pulse package and real primitive pulses.
- Decisions: retain latent noise memory or reset; exact branching or compressed
  process representation; infer correction policy from outcome correlations.
- Loop: compare endpoint agreement with conditional-history failure, revise
  state representation, test held-out schedules.
- Public evidence: short histories, unconditional maps, small aggregate checks.
- Hidden families: quasistatic drift, OU, telegraph, independent white noise,
  correlated multichannel control.
- Evaluator: conditional probability accuracy, total variation worst history,
  memory/runtime, validity of claimed benefit of feedback.
- Shortcut: small cases reduce to textbook hidden-state filtering or quadrature;
  realistic scale risks becoming a new process-tensor research project rather
  than the paper's central supported workflow.
- Rejected before build: weak paper centrality and convincing small-scale shortcut.

## 3. Repair second-order resonant integrals (rejected)
- Contribution/claim: stable full-process numerical integration.
- Assets: actual pre-fix snapshot and regression tests.
- Decisions: stable special functions, degeneracy grouping, caching policy.
- Loop: failing limit cases -> reformulation -> rerun convergence checks.
- Evidence: invariants and sparse resonance diagnostics.
- Families: degenerate controls, resonance, small time step, mixed units,
  multiqubit spectra. Most are numerical variations, not independent families.
- Evaluator: error, speed, peak memory.
- Shortcut: divided differences or direct high-order quadrature fixes the core.
- Reject: ordinary numerical repair, insufficient independent scientific choices.

## 4. Reproduce RB noise-memory slopes (rejected)
- Contribution/claim: pulse-correlation filter functions affect RB decay.
- Assets: real RB script and optimized pulses.
- Decisions: spectral quadrature, sequence sampling, finite-length fit.
- Loop: reproduce -> inspect residuals -> adjust fit/grid -> rerun.
- Evidence: sparse published aggregates and public controls.
- Families: white, 1/f, OU, narrowband, cross-correlated noise.
- Evaluator: transfer fidelity, uncertainty calibration, runtime.
- Shortcut: run repository concatenation and standard regression/sampling.
- Reject: consequential work dominated by an existing API and routine statistics.

## 5. Resource-bounded QFT filter assembly (rejected)
- Contribution/claim: modular assembly accelerates long quantum algorithms.
- Assets: real QFT script and periodic-driving example.
- Decisions: full versus partial basis, cache granularity, spectral mesh.
- Loop: profile -> cache/contract -> compare -> rerun.
- Evidence: baseline timings and small invariants.
- Families: QFT, RB, periodic DD (only three independent circuit structures).
- Evaluator: accuracy, peak memory, wall time.
- Shortcut: use official concatenate/extend and avoid dense intermediate tensors.
- Reject: copying visible implementation patterns suffices.

Only concept 1 proceeds to construction. Rejection remains mandatory if an
isolated frontier participant succeeds or the pilot's difficulty is clerical.
