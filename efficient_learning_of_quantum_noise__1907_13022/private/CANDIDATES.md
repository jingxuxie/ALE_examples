# Solution-gap mining ledger

Authoring date: 2026-08-27 (America/Los_Angeles). These are research-task candidates, not claims of established hardness. Every selected candidate receives an empirical pilot.

## Evidence acquired

- Target: the 23-page arXiv:1907.13022 manuscript, including its supplementary information; official IBM Melbourne data repository `rharper2/EfficientLearningDataSet` and analysis `rharper2/Juqst.jl`. The archived PDF is v2 (16 April 2021); the identifier originates in 2019. The 2020 sparse method is a later development relative to the original preprint and an adjacent method relative to v2.
- Later sparse reconstruction: arXiv:2007.07901; official `rharper2/sparsePauliReconstruction` includes the noisy peeling decoder and data-based extrapolation workbooks.
- Later population recovery: arXiv:2105.02885; official `sflammia/PauliPopRec.jl`.
- Later gate-set learning: arXiv:2410.03906; official `csenrui/PauliGST`, including the published implementation notebook.
- Later physical-family transfer: arXiv:2303.00780, 39-qubit syndrome-preparation circuits and 20-data-qubit graphical models. Code/data are request-only, NOT acquired; they must not be represented as an available oracle.
- Juqst history contains actual CMI index correction `08101ff` (2021-09-18), marginalization performance change `9672bcb` (2022-07-10), tests PR #8, observed-basis extension PR #9, and a stabilizer regression fix `b2f2959` (2023-05-05). Dependency-only changes in 2025/2026 are not treated as scientific gaps.

## Eight distinct directions

### A — Conditional dependence after an actual indexing fix
- Starting artifact: a compatibility adapter retaining the earlier limited dependence analysis, plus unlabeled local distributions; not the post-fix module.
- Private solution: Juqst `08101ff` and later marginal tests, with independently computed conditional distributions.
- Outcome: distinguish direct interactions from mediated correlation and recover a consistent scalable noise model.
- Shortcut: threshold pairwise mutual information.
- Failure regime: mediator chains, colliders, high-order factors; strong marginal correlation does not imply a direct factor.
- Independent bottlenecks: conditioning/index conventions, structure selection, global contraction.
- Check: held-out conditional/marginal likelihood and rare-event queries, plus exact small-instance checks.

### B — Full sparse Pauli recovery beyond locally averaged noise
- Starting artifact: unlabeled structured eigenvalue observations and a dense small-system baseline, without the later decoder.
- Private solution: official noisy peeling implementation in `sparsePauliReconstruction` and independently generated physical channel references.
- Outcome: recover arbitrary-weight heavy Pauli errors from subsampled noisy spectra.
- Shortcut: enumerate low-weight Paulis and fit nonnegative least squares.
- Failure regime: 40–100 physical qubits, nonlocal support and approximately sparse backgrounds; the ambient space is exponential.
- Independent bottlenecks: collision resolution, noise-aware support decoding, probability refinement.
- Check: nonidentity mass/support errors and predictive spectral error, stratified by family; runtime/memory.

### C — Globally normalized graphical models at 100 qubits
- Starting artifact: original local-marginal workflow and incomplete scalable inference adapter.
- Private solution: privileged precomputed contractions of source-grounded bounded-degree graphical noise models; later graphical-model analysis supplies the modeling gap.
- Outcome: infer factors from local observations, then answer global weight-tail and parity queries.
- Shortcut: dense joint reconstruction or independent-qubit multiplication.
- Failure regime: 100-qubit chains, ladders and higher-order clusters; dense states cannot be materialized, independent models miss rare correlated events.
- Independent bottlenecks: statistically consistent factor recovery and numerically stable exact/controlled contraction.
- Check: independent transfer/contraction references, small exhaustive checks, global queries and resource limits.

### D — Transfer from Clifford calibration to syndrome-preparation noise
- Starting artifact: 14-qubit calibration protocol and public device geometry.
- Private solution: 39-qubit follow-up paper's author-only data and computation, currently unavailable; published output summaries alone are insufficient for a strong executable reference.
- Outcome: correctly predict subthreshold logical failure with correlated rather than IID noise.
- Shortcut: rescale average gate infidelity or use an IID decoder model.
- Failure regime: correlated errors dominate the low-error tail; realistic cycle timing differs from isolated gates.
- Independent bottlenecks: experiment/circuit mapping, distribution extrapolation, decoding.
- Check: independently held-out logical failure estimates if actual author data become available. Not selected: unavailable reference, not predicted ease.

### E — Real-data mismatch in simultaneous two-qubit experiments
- Starting artifact: official raw IBM data in a neutral numerical container and baseline decay fit, with analysis outputs withheld.
- Private solution: official Juqst reconstruction functions and privately computed high-precision fits/validation summaries.
- Outcome: recover SPAM-robust correlated error observables across single- and mixed-twirl runs without forcing a nearest-neighbor explanation.
- Shortcut: divide depth-one by depth-zero, or fit all curves as noiseless single exponentials and clip.
- Failure regime: actual noisy decays, SPAM amplitudes, nonuniform acquisition depth, and block twirls; the paper reports markedly worse local-model fit in two-qubit mode.
- Independent bottlenecks: correct twirl/marginal inversion, constrained decay estimation, cross-component correlation consistency.
- Check: official full-data reference outputs, held-out real experiments, sensitivity to deterministic relabeling and acquisition subsets.

### F — Self-consistent gate-set learning instead of separate channels
- Starting artifact: Clifford gates, a local Pauli-noise ansatz, noisy experiments and incomplete per-gate analysis.
- Private solution: later PauliGST notebook and gauge/cycle-space characterization in arXiv:2410.03906.
- Outcome: identify learnable combinations, avoid unjustified parameter claims, and predict held-out experiments with consistent SPAM.
- Shortcut: independently fit every decay or select an arbitrary inverse/pseudoinverse and call all parameters identified.
- Failure regime: gauge directions, disconnected pattern-transfer components, spatial ansatz intersections.
- Independent bottlenecks: Clifford propagation, learnability/gauge algebra, noise-aware physical fitting.
- Check: gauge-invariant prediction and identifiability queries against private graph-based references.

### G — Missing ablation between pairwise and higher-order noise
- Starting artifact: one-/two-qubit summaries and a pairwise graphical-model baseline.
- Private solution: official full 14-qubit distributions plus higher-order marginal routines and private exhaustive ablation outputs.
- Outcome: determine whether pairwise agreement conceals a consequential high-order correlated-noise branch.
- Shortcut: report covariance agreement as full validation.
- Failure regime: different channels can share pairwise marginals while having different high-order tails.
- Independent bottlenecks: choose informative observables, fit competing structured models, avoid overfitting finite shots.
- Check: held-out higher-order distributions and predictive scores. Not separately built: overlaps the real-data pilot's scientific outcome, not rejected on predicted ease.

### H — Shot-efficient population recovery versus noise amplification
- Starting artifact: product-basis measurement records, a known heralded-failure probability and a small exhaustive estimator.
- Private solution: PauliPopRec implementation, including its Proposition-27 estimator and heralded-failure argument `v` in the supported interval 0–1/4, plus tutorial/tests.
- Outcome: recover significant arbitrary-weight errors without exponentially unstable inversion.
- Shortcut: full channel inversion, total recall without pruning, or ignoring heralded failures.
- Failure regime: many qubits with heralded measurement failures, where inversion amplifies statistical errors and retaining every positive empirical estimate overfits. The actual source documents an unoptimized O(m*n^2/threshold) implementation; no faster hidden release is claimed.
- Independent bottlenecks: significant-prefix search, noise-robust population estimation, allocation of confidence.
- Check: known physical sparse channels and held-out measurement likelihood. Reserve candidate; four pilot slots prioritized for distinct artifacts and outcomes, not a prediction of generic solvability.

## Four selected pilots and anti-compression gates

1. `concept_01_sparse`: direction B. A fixed sparse-Walsh solver is possible, but full direct methods fail at exponential ambient size and collision/noise handling are distinct bottlenecks.
2. `concept_02_gateset`: direction F. Generic regression only applies after the nontrivial Clifford/gauge representation is constructed; identifiability and prediction are separately scored.
3. `concept_03_experiment`: direction E (with G). Nonlinear regression alone does not implement mixed twirl inversion or infer correlations; real acquisition data expose mismatch.
4. `concept_04_graphical`: direction C, with A used as a reference-regression audit. The participant is not an actual pre-fix Juqst checkout, so this must not be represented as an empirical repository-bug-repair pilot. A contraction kernel alone does not infer factors; the pilot tests whether combining that step with global inference is genuinely difficult. Subsequent empirical audits can still reveal a universal composite shortcut.

No empirical hardness conclusion is made here. Minimal pilots, reference passes, isolated attempts and source-grounded counterexamples determine acceptance.
