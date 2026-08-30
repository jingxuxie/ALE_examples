# Stim hardness discovery

Generation date: 2026-08-28. Seed: Craig Gidney, *Stim: a fast stabilizer circuit simulator*, arXiv:2103.02202v3 (2021-06-18), Quantum 5, 497 (2021).

## Source trail

- Paper and ancillary code listing: https://arxiv.org/abs/2103.02202 and https://arxiv.org/html/2103.02202v3 . Sections 2–5 motivate exact Clifford semantics, Pauli-frame error signatures, detector events, and the distinction between simulation throughput and downstream combinatorial problems.
- Official source: https://github.com/quantumlib/Stim . Remote HEAD observed during generation: `79ae4f118ca11c615d6d8de7c6eed7d189d3a6eb`.
- Pinned independent generation-only verifier: Stim 1.15.0 binary wheel. No Stim source, wheel, private witness, evaluator, prior attempt directory, or generator is mounted for tested agents. Concept 2 generation 2 deliberately supplies a current-champion baseline as a public task asset; it does not expose the champion's original attempt directory or private challenge results.
- Detector-error-model specification: https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md . Categorical Pauli branches must not be silently replaced with independent detector flips.
- Later release notes and repository issues were inspected by the research worker; its detailed primary-source notes are in concept_3/adversary/concept_research.md.
- Previous local Stim commissioning task and passing private solution were inspected at `tasks/stim_a_fast_stabilizer_circuit_simulator__2103_02202`. Its exact exhaustive subset/policy implementation had at most 20 correction cells. Concept 1 instead scores improvement at larger combinatorial size and does not demand agreement with a reference optimum. No successful prior fresh submission was present there (the recorded 600-second attempt timed out).

## Concepts considered before construction

1. **A: robust detector-tap compression. Selected.** Joint combinatorial selection and one deterministic minimax correction policy, with exact hidden channel risk and an explicit relative improvement target. Extends a prior small exhaustive problem without requiring a global optimum.
2. **B: low-weight logical-fault falsification. Selected.** Produce a sparse, physically realizable zero-detector, odd-logical fault set defeating an overconfident wrapper around truncated syndrome search. Private constructive certificate; independent algebra and Stim validation.
3. **C: topology-constrained exact Clifford design. Selected.** Recover a compact native local circuit for a signed target tableau, starting from a much larger correct routed baseline. Private compact witness; exact semantics and resource verification.
4. A: density-adaptive frame simulation. Rejected for this tournament: implementing standard dense/sparse switching risks reducing to reproduction of existing simulator code and performance noise.
5. F: repair nested-repeat detector-model folding. Rejected: later public source patches could reduce this to package replication, while isolating a nontrivial trustworthy regression suite would be costly.
6. D: predict rare logical failures from finite syndromes. Rejected: careful Bayes-risk and statistical-power calibration would dominate the task package and could confound hardness with label noise.
7. E: active calibration of correlated Pauli channels. Rejected: gauge identifiability and query-accounting audits are tractable, but a target could accidentally be unidentifiable rather than difficult.
8. C: hook-safe syndrome-extraction schedules for a surface-code patch. Rejected: well-known local hook-orientation schedules may be immediately recovered; arbitrary topology twists risk hiding trivial infeasibility.
9. B: small non-Pauli noise counterexample to frame reuse. Rejected: the paper explicitly restricts its noise model, so violating that assumption would be a trivial and scientifically invalid falsification.
10. A: near-optimal random-Clifford gate cancellation without topology. Rejected in favor of concept 3: topology and exact signed tableau constraints create a more substantial search problem than local cancellation alone.

Only concepts 1–3 are built. Candidate research is generation-only; it is not fresh-agent evidence. The empirical tournament must use the supplied allowlisted runner, ultima-alpha, a fresh runtime, and a one-hour limit for each attempt. Administrative execution failures do not count as scientific hardness.

## Decision rules

Concept 1's target is fixed before launching any tested agent: mean relative improvement at least 0.20 and each family's mean at least 0.10; every output valid and inside runtime/memory limits. Failure without a passing resource-compliant private optimizer is `hard_open_candidate`, not proof of impossibility.

Concepts 2 and 3 validate static artifacts directly. A failed fresh attempt with a validated private witness is `hard_verified_achievable`. A solved concept is promoted to a champion and privately challenged before any ratchet. No more than three champion-ratchet generations per concept are allowed.

## Empirical ratchet record

Both initial counterexample agents found valid 20-fault logical words using information-set search. Their submissions and original evaluator remain archived; this solved generation was not silently regraded on new data. The faster completed submission became `concept_2/champions/generation_1/`.

The unchanged champion executable was then run in the audited evaluator sandbox on eight private models spanning witness weights 24, 28, 32, and 36, two independent seeds each. Every model retained 512 fault locations and 192 detector checks. Every returned best word was exact but too heavy (52–56 faults). Thus the failure was not an interface error, a new file format, or larger inputs. The source's four-nonpivot search has inadequate low-weight coverage in this higher-distance regime. Generation 2 fixes the strongest observed 36-fault case, supplies the champion source and its 56-fault best artifact as the baseline, and retains an independently validated private 36-fault witness.

Both witness tasks use explicit physical Clifford instruments and full exact property checks, not comparison with a canonical answer. The counterexample model's raw random columns are generated using domain-separated HMAC-SHA256 with private entropy; an exposed-PRNG-state shortcut was removed before any tested agent received it. Initial construction and ratchet audits check native fault signatures, matrix rank, observable independence, and rejection of heavier exact logical words.

Generation-only official source inspection additionally covered `src/stim/search/hyper/algo.cc`, the cutoff-search API warnings in `src/stim/circuit/circuit.pybind.cc`, and the last eight archived commits through `79ae4f118ca11c615d6d8de7c6eed7d189d3a6eb`. The task attributes the false certificate to its supplied wrapper, never to Stim's explicitly heuristic API.
