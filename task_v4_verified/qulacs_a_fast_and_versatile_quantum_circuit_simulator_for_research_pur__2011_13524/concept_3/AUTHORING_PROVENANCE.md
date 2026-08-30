# Authoring provenance

## Primary paper verification

Verified on **2026-08-28** against Suzuki et al., *Qulacs: a fast and versatile quantum circuit simulator for research purpose*, arXiv **2011.13524v4**, revised **2021-10-05**, published in *Quantum* **5**, 559 (2021).

Primary records: `https://arxiv.org/abs/2011.13524v4` and `https://arxiv.org/pdf/2011.13524`. Journal DOI: `10.22331/q-2021-10-06-559`.

Section **3.2**, “Performance analysis of quantum error correction schemes,” motivates accurate noisy-circuit simulation with realistic noise models. Section **3.3**, “Generation of a reference of experimental data,” connects simulation references to characterization and calibration of qubit controls. Both appear on printed page 5 of the verified paper. These sections motivate this task's use of a fast, explicit noisy simulator for experimental calibration; they do not themselves specify this benchmark or an adaptive design algorithm.

## Authored extension, not a paper reproduction

Primary verification category: **E — ACTIVE EXPERIMENT DESIGN**. The task is an authored inverse problem: ten-parameter two-qubit conditional/Bell Ramsey calibration, shot and query budgets, multimodal frequency likelihoods, Gaussian correlated dephasing, effective SPAM nuisance, three disclosed prior families, and a predictive/parameter objective. The Hamiltonian, action set, priors, scoring scales, numerical baseline, and threshold are author choices, not claims copied from Qulacs. A closed-form small-system simulator avoids a Qulacs installation while preserving a physical quantum state/channel/POVM interpretation. The independent 4-by-4 density-matrix tests verify that interpretation.

The equations alone are not the answer: a strategy must choose a finite collection of noisy measurements, resolve aliases, separate visibility/offset/envelope effects, and allocate correlation-sensitive Bell probes while preserving frequency precision. `rho` is entirely absent from local-probe likelihoods, and uniform integer-time schedules have exact coherent aliases. Public code exposes all physics and prior supports; no hidden facts or external literature are needed by participants.

## Calibration versus fresh-agent discovery

No fresh agent, parallel agent, or participant attempt was launched. The user authorized parallel generation, but authoring here used ordinary local processes only. Baseline measurements and observation-only adaptive policy experiments are privileged **authoring calibration probes**, not held-out fresh-agent successes. Their parents can access the private evaluator, but their strategy subprocesses use only the controlled JSONL inputs and public fitting/simulator assets. The suite was generated once before calibration and never rerolled to improve scores.

The numerical calibration record, chosen fixed target, artifact hashes, and remaining isolation integration work are recorded in `adversary/CALIBRATION.md`, `adversary/freeze_manifest.json`, and `status.json`. The target is fixed before any future fresh-agent launch. The parent workflow should conduct independent fresh-agent hardness discovery only after applying its isolation wrapper; this package does not claim that such a study has already occurred.
