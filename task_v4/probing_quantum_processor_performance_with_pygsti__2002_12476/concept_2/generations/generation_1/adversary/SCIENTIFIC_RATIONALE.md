# Private generation record — not participant material

## Scope and scientific claim

Primary verification mode: **B, counterexample/falsification**. Only concept_2 was built by this worker. No fresh agent was launched. The engineering claim under test is deliberately local: the supplied reset-reduced qubit model passing the supplied compressed calibration screen is sufficient to predict a same-depth application circuit. It is not a claim that pyGSTi contains this exact reset-reduction algorithm, nor a purported refutation of a GST or RPE theorem.

The stationary physical device is a qutrit with three fixed unitary gates. Two computational levels implement I, X(pi/2), and Y(pi/2); a weak Hamiltonian couples them to one leakage level. A gate-dependent leakage phase is physical and does not affect the specified ideal computational action. State preparation and two-outcome readout are fixed, positive, and normalized. There is no postselection, random simulation, hidden circuit counter, hand-coded trigger, or participant-specified acceptance data.

The supplied reported map for a gate has two Kraus operators: the computational block of its unitary and a matrix that transfers leakage probability to computational state 1. Their completeness follows immediately from the first two columns of the unitary. Thus both physical and reported models are CPTP, and their single-gate outcome probabilities agree. The reduced model discards coherent leakage history; the physical model does not. The evaluator explicitly checks unitarity and Kraus completeness in addition to the by-construction guarantee.

The calibration data use the official XYI lite germs and per-germ fiducial-pair lists, with all lengths 1,2,4,8,16,32,64, exhaustive words through length four, and 32 fixed independently generated random 64-gate guards. This is a fully specified custom FPR-inspired design, not a byte-for-byte pyGSTi experiment-design export. The short-depth convention uses at least one whole germ. There are 270 distinct calibration circuits, 282 family memberships, and maximum complete-circuit depth 70. The application circuit has 64 gates and at least four occurrences of every API operation.

The requirement of at most 1% final leakage, but at least 6.5 percentage points of binary outcome discrepancy, prevents a witness consisting only of accumulated final leakage population. The exhaustive short circuits and long germ families reject the naive resonant-idle example; that rejection is tested. Five explicit parameter perturbations require reproducibility against +/-2% coupling scale and +/-0.002 radian common leakage-phase shift. They are discrete scenarios, not a certified continuous uncertainty interval.

## Primary source provenance

Accessed August 28, 2026. These links are for generator provenance only; the participant needs no internet or pyGSTi installation.

- Seed paper, Nielsen et al., *Probing quantum processor performance with pyGSTi*, arXiv:2002.12476: https://arxiv.org/pdf/2002.12476 . Section II names prediction on future circuits as a characterization objective; Section III describes structured periodic GST circuits and Markovian models; Section V.A.1 explains FPR's reduction in experimental size at a cost in robustness. The present task isolates that model-acceptance-to-prediction extrapolation in a finite, independently checkable setting.
- Official XYI model pack: https://raw.githubusercontent.com/sandialabs/pyGSTi/master/pygsti/modelpacks/smq1Q_XYI.py . Consulted the six fiducials, five lite germs, and lite per-germ fiducial-pair data. The actual task circuit strings are stored explicitly in both public and trusted input assets and are SHA-256 pinned; future upstream edits cannot affect scoring.
- Official leakage guide: https://pygsti.readthedocs.io/en/docs-preview/markdown/guides/gst/Leakage.html . Motivates the three-level versus reduced two-level modeling distinction, including leakage amplitude returning with phase memory.
- Official bad-fit guide: https://pygsti.readthedocs.io/en/docs-preview/markdown/guides/gst/BadFits.html . Distinguishes the fixed-gate model assertion from real history-dependent behavior and cautions that model violation must be interpreted in its physical/model context.
- GST theory review, Nielsen et al., *Gate Set Tomography*, arXiv:2009.07301: https://arxiv.org/abs/2009.07301 . Follow-up grounding for model structure, experiment reduction, and model validation.
- Blume-Kohout et al., *Demonstration of qubit operations below a rigorous fault tolerance threshold with gate set tomography*: https://www.nature.com/articles/ncomms14485 . The authors explicitly discuss leakage and correlated errors outside the Markovian qubit model; this task does not assert a guarantee outside that model's assumptions.
- Official release history: https://github.com/sandialabs/pyGSTi/releases . Inspected leakage-aware modeling, gauge optimization, and confidence-interval follow-ups (#699/#707). No release-specific code or bugs are prerequisites for solving this task.

## Fixed target and generation asymmetry

All five scenarios must meet maximum calibration error <=0.005, each calibration-family RMS <=0.002, held-out error >=0.065, and final leakage <=0.01. Nominal coupling norm per gate is <=0.04 radian. Numerical comparison tolerance is 1e-10. The target represents a large same-depth predictive failure despite small calibration residuals, not a score chosen from a fresh agent's output.

Generation used a fast statevector/Pauli-transfer simulator, random processor proposals, evolutionary circuit search, and alternating constrained processor/circuit optimization. Exploratory nominal-only searches informed the target before any fresh attempt. The initial 12 pilot records predate correcting the final fiducial from YYY to the official YY; they are exploratory seeds, not final calibration evidence. All subsequent joint searches and final evaluations use the corrected circuit family. Private scripts, negative examples, search traces, and best witnesses remain exclusively under adversary/. The participant receives the physics and executable screen but none of these search artifacts. No undisclosed scientific criteria are used by the evaluator. The final robust portfolio was stopped after its recorded completed iterations to hand the frozen task to the main session; this is not an exhaustive impossibility search.

The final robust search and baseline are rescored by a separately implemented density-matrix/Kraus simulator whose unitaries use scipy.linalg.expm rather than the public analytic rank-two exponential. Analytic one-gate and repeated-idle identities, Choi positivity, trace preservation, malformed JSON, and agreement on 41 processor parameter sets are audited by adversary/audit.py. Frozen hashes and achieved scores are recorded in status.json and adversary/freeze.json.

## Hardness interpretation

The retained target is 0.065 in the worst of five scenarios, subject to all other constraints. A private candidate below that threshold is not a solution. If no passing private witness is recorded, solvability remains **unknown**, not disproved. Fresh-agent testing is the main session's responsibility. Until that testing occurs, empirical hardness is **pending**; a fresh failure with no passing privileged witness supports hard_open_candidate, not hard_verified_achievable.
