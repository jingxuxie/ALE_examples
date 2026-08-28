# Anti-compression evidence and limits

## Distinct technical components

1. **Clifford/channel representation.** Inputs contain primitive circuits and local factors, not a design matrix or graph. Solving requires signed reverse propagation, the declared pre-gate frame, factor-restricted anticommutation features, and separate preparation/readout contributions. The dense simulator and independent binary-sign checks validate these conventions.
2. **Gauge versus experimental incompleteness.** Structural learnability is determined over all permitted experiments. It differs from the row span of finite calibration in the restricted-sector family, including its genuinely connected large devices. Only gauge-invariant, calibration-supported query values are evaluated; parameter vectors are never targets.
3. **Finite-shot prediction.** Repeated cycles include low-signal and sometimes negative sign-corrected empirical contrasts, with heterogeneous shot budgets. A logarithm followed by unweighted least squares is statistically different from the input-only binomial reference. Novel circuit compositions and signed contrasts must be predicted, not memorized per decay curve.

These are integrated but separately scored (35%, 25%, 40%). The score is `scale/(scale+loss)` with `scale=weak_loss/4+12*reference_loss`, so it has neither a clipping plateau nor an acceptance tolerance. This calibration controls dynamic range; it is not itself evidence of accuracy or hardness. Absolute errors and independent physical checks are additionally recorded.

## Scale and scientific families

| Family | Core size | Parameters | Calibration versus structural rank |
|---|---|---|---|
| Individual local CZ/CX edges | 4, 6, 20 qubits; 3, 5, 19 noisy gates | 53, 87, 325 | 49/49, 81/81, 305/305 |
| Alternating parallel layers with nearest-neighbor crosstalk and correlated SPAM | 6, 8, 20 qubits; 2 noisy layers | 148, 224, 540 | 142/142, 216/216, 520/520 |
| Restricted-sector calibration: small patches, then a connected 20-qubit chain | 6, 8, 20 qubits; 2 noisy layers | 102, 136, 502 | 72/96, 104/128, 98/482 |

There are exactly 9 precomputed core and 6 disjoint challenge cases. Each family has one connected 20-qubit core case. Every challenge is a connected 20- or 24-qubit system, with up to 24 individual noisy gates, as many as 672 parameters, lower/more uneven shot budgets and longer amplification. Large restricted-sector cases use a connected chain/ring calibrated only in the computational Pauli sector; they do not replicate disconnected small blocks. Both ideal-interaction and noise-factor graph connectivity are asserted during generation and testing. Core cases contain 204–1,860 training records; challenges reach 2,316. Each hidden case has 112 mixed channel/cycle/contrast queries and 128 held-out circuits. The sole public example remains 2 qubits, 53 training records, 20 queries and 16 held-out circuits. Seeds, qubit permutations, library order, factor order, Pauli axes, rates, shot allocations and query order vary.

This is a realistic local gate-set scale, not exponential ambient dimension as an excuse for hardness. No sparsity search is needed: all declared generator supports are populated. The contrast with sparse reconstruction is substantive.

Before changing pools, the unchanged compressed reference passed independent connected crosstalk probes at 20 and 24 qubits: scores 0.99853/0.99827, peak RSS 257.27/336.95 MiB, and 12.53/8.78 seconds under the existing sandbox limits. The 24-qubit probe uses 6,048 rooted experiments and 672 parameters, enumerating local dependency scopes of at most four qubits, not a full `2^24` graph. Held-out propagated Pauli supports reach 18 qubits in the active 24-qubit crosstalk challenge. The final active-pool reference runs peak at 340.67 MiB and 8.08 seconds per case. Timing variation reflects different cases and shared-machine load; it is not evidence that larger systems are faster.

## Measured author ablations

`ablation_report.json` contains all case/component losses and family results. The ablations below generously retain correct source-derived geometry or labels when isolating a statistical or propagation failure; they are not stand-alone participant submissions.

| Method | Core mean / worst family | Challenge mean / worst family |
|---|---|---|
| Strong input-only reference | 0.99165 / 0.98317 | 0.99223 / 0.98010 |
| Sign-aware scalar per-gate weak baseline | 0.22300 / 0.20571 | 0.22177 / 0.20336 |
| **Correct geometry and labels supplied**, unweighted log least squares | 0.63010 / 0.51105 | 0.60576 / 0.43216 |
| Exact reference except treating finite design rank as structural gauge | 0.94776 / 0.86293 | 0.94399 / 0.85358 |
| Exact reference predictions but every query declared identifiable | 0.71165 / 0.70317 | 0.71223 / 0.70010 |
| Correct labels and signed counts, but frozen Pauli support during fitting/prediction | 0.77954 / 0.73319 | 0.85601 / 0.70985 |

Thus the particular universal kernel “take logs and pseudoinvert” fails even after the actual domain representation and labels are donated. The public interface does not donate them. The weak baseline already handles ideal signs, so its failure is not manufactured by ignoring a trivial sign convention.

## What is NOT established

- No proof excludes a short, well-designed solver that implements the necessary Clifford algebra, learns the relevant row spaces, and performs a suitable constrained statistical fit. Calling every numerical estimator a universal kernel would obscure rather than resolve that question.
- Using finite calibration rank as structural gauge still exceeds 0.9 in **mean**, despite failing the restricted family's worst-family score. Reporting worst-family performance is essential; average-only acceptance would miss this scientific error.
- The frozen-support ablation reaches about 0.93 on two challenge families while failing local edges. The current challenge set is not uniformly harder on every mechanism. It provides lower-shot/longer-cycle and coverage stresses, not a guarantee of stronger difficulty. The scale correction demonstrates feasible genuinely coupled processing, not increased participant hardness.
- The production solver never enumerates the full structural graph, but it still uses dense SVD and likelihood products on the compressed model. The measured claim stops at 24 qubits; no graph-linear implementation or hundred-qubit runtime is asserted.
- Scores are calibrated to the measured source-derived reference. Its high score is supplemented by independent physics, source, gauge and absolute-error tests; calibrated score alone would be circular evidence.
- No fresh agent or participant attempt has been launched. The main author owns isolated ultima-alpha attempts and any empirical acceptance decision.

## Later ratchet

Regenerate with an unseen seed before any attempt-specific tuning. Promote challenge profiles only after measuring their family/component gaps. If support-insensitive models remain competitive on a family, favor noncommuting compositions with moderate observable contrast and anisotropic spectator terms rather than merely increasing size, depth, or noise. If finite-rank heuristics pass an average-only threshold, require a reported worst-family threshold or distribute calibration-sector holes across additional scientific families. Any changed design must rerun the complete independent-check suite and both isolated reference pools; do not install gauge-dependent planted coordinates as targets.
