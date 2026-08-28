# Counterexample audit: reject as robustly solved

**Decision: no genuine counterexample or focused ratchet is supported. Treat concept 01 as robustly solved by the frozen submission within this bounded audit.** Do not escalate small probability-estimation differences into a failure claim. No active task, cases, grading, targets, reference, or frozen solver were changed; no model or fresh agent was launched.

## Fixed experiment and absolute reference eligibility

Twelve fresh cases were specified and generated before any solver runs: two independent seeds in each of six regions. The complete specification and seeds are in `PLAN.md` and `plan.json`. Shifts include 384 heavy terms in 128 bins per group, bin noise up to 0.32 times the smallest heavy probability, 100 qubits with 480 terms and roughly 9000-fold range, nearly equal collision amplitudes, an 8192-term physical background carrying 6% of nonidentity mass, and known heteroscedastic measurement errors. Hash widths 6, 7, and 8 and group counts 3 and 4 are exercised, without changing the current observation or output contract.

All **12/12** pass the required input-only existing-reference gate: score >0.9, significant-support F1 >=0.98, and uncapped raw loss <0.1. **No cases were excluded, replaced, or resampled.** In fact, reference F1 is 1 on every case and maximum raw reference loss is 0.0558257021. Thus this result is not manufactured by recalibrating an inadequate reference. Reference and frozen submission use exactly the same per-case reference/weak calibration and the unchanged uncapped `metrics.measure` / `metrics.grade` functions.

## Results

| Region (two seeds each) | Reference mean | Frozen mean |
|---|---:|---:|
| Higher load | 0.999423041 | 0.999435698 |
| Sign-noise boundary | 0.999530368 | 0.999546797 |
| Range and dimension boundary | 0.999999929 | 0.999999929 |
| Nearly equal collision amplitudes | 0.997919203 | 0.997955085 |
| Approximately sparse boundary | 0.963117079 | 0.962907821 |
| Known heteroscedastic errors | 0.999996092 | 0.999998282 |
| **All twelve** | **0.993330952** | **0.993307269** |

- Frozen minimum score: **0.962837757**; maximum score deficit to the reference: **0.000233650**.
- Frozen and reference both recover **all 3752 planted significant Pauli labels across these cases**, with significant-support F1 **1 on every case**, identical true-heavy label sets, and **zero absent heavy probability mass**.
- Maximum nonidentity distribution L1 difference between frozen and reference, including unresolved uniform mass and divided by true nonidentity mass: **0.001075729**, about **0.108%**. This is actual probability agreement, not only agreement on thresholded support.
- Maximum matched-heavy probability relative L1 error against planted truth: **0.004139559 frozen**, **0.004157009 reference**. Both estimate the recovered physical probabilities accurately.
- Maximum frozen uncapped raw loss: **0.055970450**. The small worst deficit is in the approximately sparse region, not a reproducible breakdown: support is still complete and numerical probability disagreement is tiny.
- Maximum recorded frozen runtime: **2.284 seconds**, well within the unchanged 120-second / 2 GiB limits.

`results.json` contains every score, uncapped loss, runtime, seed, eligibility reason, probability comparison, missing-label diagnostic, and the above-floor diagnostics. Per-case input, truth, reference, weak, and frozen NPZs are retained under `cases/`. Atoms above twice the floor are additionally compared when that subset exists. The nearly flat cases have no such atoms; their empty diagnostic subset is marked not applicable, not scored or treated as failure. An audit-only empty-set division was corrected without modifying or regenerating any case.

## Why no shortcut counterexample emerged

Static inspection finds an input-driven general sparse-Walsh reconstruction algorithm, not a planted-answer lookup, family/seed switch, dense enumeration, or identity-dominated fit. The frozen implementation constructs support from the supplied hashes/offsets, combines soft parity-syndrome decoding and cross-group checks with pair/XOR-doubleton/triple recovery, and estimates probabilities using constrained weighted fitting with a uniform remainder and adaptive residual weights. Its dimensions are inferred from input rather than hardcoded to the original bin count or qubit count. The observed generalization is consistent with that implementation.

There is no substantive failure root cause to report and no justified focused ratchet from these observations. In particular, no axis-label or output-schema issue is counted as a scientific failure; all outputs pass unchanged validation and direct physical label matching. The strongest negative result is that both collision/support recovery and actual probability estimation remain correct under the tested shifts. An unsupported harder load/noise regime where the existing reference also breaks would not rescue this candidate, and none is proposed here.

## Independent physics and preservation checks

The generator reuses existing Clifford-generated commuting hashes and binned observation construction, but validates clean observations through the independent direct Pauli-commutation implementation. Every hash is checked for full row rank and symplectic commutation. Thirty-two randomly selected observations per group agree with the direct physical evaluator to a maximum absolute error of **3.330669074e-16**; 384 independent nonidentity probes per case supply the existing spectral metric. The planted channel has unique arbitrary-weight Pauli errors, nonnegative normalized probabilities, and subthreshold background atoms where applicable. No truth, labels, seed, or calibration result is provided to any child solver.

Reference, baseline, and frozen runs use the existing Landlock runner, with only its temporary root redirected in memory into this audit directory. The evaluator and solver sources remain unchanged. Before/after SHA256 inventories agree for **113 protected files**, including participant files, original pools and targets, evaluator/reference code, and the frozen submission. Frozen SHA256 remains `1996fc1f78936055adf84e5ebca607c0dfae8b0b832077e4769f8716891c73a4`.

## Reproducibility and scope

From the concept directory, the exact executed entry points were:

```bash
python -B private/reference/counterexample_audit/audit.py prepare
python -B private/reference/counterexample_audit/audit.py run
```

The existing plan refuses regeneration; rerunning `run` preserves cases and reuses completed result records. All audit writes are contained in `private/reference/counterexample_audit/`. The conclusion is bounded to these twelve predefined, source-grounded shifts, not a universal theorem about all conceivable contract-valid channels. It is sufficient to **reject further ratcheting on the basis of this audit and mark this pilot robustly solved**, rather than forcing a failure.
