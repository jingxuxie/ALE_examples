# Experimental oracle / fit-policy author audit

## Finding

**Reject interpreting the present low oracle score as established scientific hardness.** The numerical oracle correctly implements its pinned Juqst convention, but substantially penalizes defensible estimators with comparable held-out predictions. The four score components are not four independent scientific failure signals: all are functions of the reconstructed distribution. No scorer, target, participant, submission, pool, or grading weight was changed.

The finalized submission has **no demonstrated correlation, categorical-CMI, or DAG/JSD implementation failure on these four inputs**: recomputing all three diagnostics from its own probabilities reproduces its answers to approximately `2.5e-15` maximum absolute error. Its remaining oracle disagreement is in the reconstructed distribution and propagates into all four components. This does **not** establish that its estimator is optimal, or that its difference from the reference is only the cutoff. In particular, its mixed-acquisition interior and low-order predictions are materially worse than the reference; those limitations are reported below.

The strongest estimator-ambiguity control is ordinary full-range bounded least squares. It receives mean score **0.699194**, rather than 1, while its raw held-out RMSE differs from the reference by at most **0.173%** on any acquisition. Its projected-channel RMSE differs by at most **0.743%**, and its interior-depth predictions improve on all four acquisitions. Thus the current oracle cannot separate a meaningful scientific failure from merely choosing a different defensible fit policy. This finding does not require declaring the finalized submission uniformly superior.

## Scope, sources, and reproducibility

- Exactly `single_0`, `mixed_a_0`, `mixed_b_0`, `mixed_c_0`: four original full acquisitions, each with 11 depths and 14 qubits. No truncated variants or challenge cases were evaluated. The four-case mean here is **not** the official core/challenge aggregate.
- Read `../solver.py`, `../build.py`, `../../evaluator.py`, `../PROVENANCE.md`, participant `TASK.md` / `input/FORMAT.md`, and root-private `RESEARCH_AUDIT.md`. The existing evaluator's `errors` function and unchanged scales `0.12 * weak_loss + [0.001, 0.001, 0.00001, 0.0005]` supply every oracle score below.
- Primary source: root-private `sources/Juqst.jl/src/marginal.jl:144`, especially lines 155–166, at commit `f43c5e09acf74f335d9572297ae8e11edd34d2d6`. The code uses `first*(1+1/16)/4 = 17*first/64`, includes the crossing observation, and enforces three observations.
- Primary source: root-private `sources/1907.13022.pdf`, arXiv v2, Methods on PDF page 8. Its additive threshold is `(first+1/16)/4`, discarding the crossing and later observations; the mixed protocol explicitly retains a minimum of three. This audit keeps the minimum-three safeguard for both protocols to isolate fit policy. Supplement IV, PDF pages 19–20, discusses consistency of marginal reconstructions and leaves the best covariance-estimation method open. This is context, not an exemption from predictive testing. PDF SHA-256 verified: `4867308d9d0033d9d0cbe1cf723cb00d569c4b8cd22588b4c1ba611af93c7684`.
- Only finalized `private/runs/pilot/submissions/concept_03_experiment.py` was executed. SHA-256: `48d02d4a1436c7ddb5cdf33f6659a853e3ff7c553f642dadd73fff2e111a022d`. No live attempt contents or other pilots were inspected; no fresh agent was used. Its source was not needed for the numerical diagnosis.
- NumPy `1.21.5`, SciPy `1.8.0`; single-threaded numerical libraries. Execution took **228.675 seconds**: 192 policy fits and 48 isolated frozen-submission executions, each submission run retaining the existing 120-second / 3-GiB limits. All staging, logs, and results are confined to this directory. Hash checks confirm all 15 protected inputs, targets, task/format, manifest, and reference/scoring files stayed unchanged; the submission hash stayed unchanged too.

From the ALE workspace root:

```bash
AUDIT=tasks_v3/efficient_learning_of_quantum_noise__1907_13022/concept_03_experiment/private/reference/policy_audit
python -B "$AUDIT/audit.py" \
  --submission tasks_v3/efficient_learning_of_quantum_noise__1907_13022/private/runs/pilot/submissions/concept_03_experiment.py \
  --output rerun.json
```

Omit `--submission` for the four-policy-only audit. The option accepts only the finalized root-private submission path, never a live attempt. `--output` must be a JSON file directly inside this directory. `results.json` contains full-precision losses, scales, scores, per-depth residuals, validation errors, hashes, and timings; `run.log` is the original execution log. `audit.py` and this report complete the four-file sidecar.

## Fixed policies and held-out protocol

All audit estimators use the same histogram normalization, Walsh transform, bounded model `alpha * lambda**depth` with both parameters in `[0.01, 1]`, and Euclidean probability-simplex projection. Only the fit observation policy changes; none was tuned against targets or CV results.

| Policy | Training objective |
|---|---|
| Juqst | Exact existing reference; multiplicative cutoff, crossing included, minimum three. |
| Paper | Additive Methods cutoff, crossing excluded subject to minimum-three override. |
| Full | Same ordinary bounded least squares using all available training depths. |
| Late-weighted | Smooth tail suppression: `weight(depth) = (1 + depth / median(positive training depths))**-2`. A fixed sensitivity control motivated by the source's tail concern, **not** a claim that the paper prescribes this particular weight. |

Paper versus Juqst changes the selected window in **13,946 / 16,383** single-acquisition modes, but only **9, 8, and 10 / 16,383** mixed A/B/C modes. Even those few changes can propagate through simplex projection and the derived diagnostics; they are not negligible in the existing scores.

Each held-out calculation removes **one entire acquisition depth** before fitting, reselects the cutoff using only the remaining observations, and predicts all **16,383 nonconstant parity modes** at the omitted depth. No held-out counts or targets determine rates, cutoffs, weights, or amplitudes. All eleven folds are evaluated; no mode subsampling is used for prediction.

- **Raw RMSE:** predictions from the fitted, pre-projection rates and fitted amplitudes. The submission does not expose those parameters, so it has no raw entry.
- **Projected RMSE:** transform the reconstructed physical distribution back to parity rates, then fit only the nuisance amplitude on *all training depths*, with the same bounds and unweighted objective for every method. This also applies to the submission, which is rerun on each ten-depth input. It is a common comparison of the actual returned channels, not only of unphysical pre-projection rates. Policy-weighted amplitude-refit residuals are additionally retained in JSON.
- **Interior RMSE:** projected predictions for the nine non-endpoint held-out depths. **Low-order RMSE:** projected predictions over all eleven depths but only the 105 one- and two-qubit parity modes. Every RMSE is the square root of the mean squared residual, not an average of per-fold RMSEs.

These are finite-record predictive comparisons, not a ground-truth physical-channel certificate or a significance test. Walsh modes are correlated; four acquisitions are not thousands of independent experiments. Independent mode-wise nuisance amplitudes are used as in the fitting model. The reference and all alternatives can be affected by acquisition heterogeneity and model mismatch.

## Existing score components

Component order is probability loss away from identity, group-event correlation, categorical CMI, and DAG Jensen–Shannon **distance**. Each component uses the existing scale/(scale+loss) mapping. Juqst reproduces every stored probability target exactly; independently recomputed diagnostics introduce only floating-point differences, with mean scores within `5e-12` of 1 (individual components within `2e-11`).

| Acquisition | Policy | Mean | Probability | Correlation | CMI | DAG JSD |
|---|---|---:|---:|---:|---:|---:|
| single | Juqst | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| single | Paper | 0.636425 | 0.952981 | 0.387545 | 0.399218 | 0.805954 |
| single | Full | 0.608422 | 0.958566 | 0.366432 | 0.465789 | 0.642902 |
| single | Late-weighted | 0.643419 | 0.971929 | 0.401288 | 0.466933 | 0.733526 |
| single | Frozen | 0.565910 | 0.943044 | 0.251477 | 0.407585 | 0.661532 |
| mixed A | Juqst | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| mixed A | Paper | 0.699293 | 0.899764 | 0.673218 | 0.339024 | 0.885169 |
| mixed A | Full | 0.647096 | 0.815321 | 0.606786 | 0.276472 | 0.889805 |
| mixed A | Late-weighted | 0.838485 | 0.924158 | 0.825384 | 0.625302 | 0.979097 |
| mixed A | Frozen | 0.331023 | 0.410789 | 0.387129 | 0.105115 | 0.421059 |
| mixed B | Juqst | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| mixed B | Paper | 0.822417 | 0.896588 | 0.684946 | 0.821611 | 0.886523 |
| mixed B | Full | 0.763087 | 0.795311 | 0.566290 | 0.838269 | 0.852479 |
| mixed B | Late-weighted | 0.861077 | 0.912732 | 0.764118 | 0.824043 | 0.943416 |
| mixed B | Frozen | 0.371931 | 0.390225 | 0.359377 | 0.369213 | 0.368911 |
| mixed C | Juqst | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| mixed C | Paper | 0.889477 | 0.942465 | 0.800967 | 0.901406 | 0.913071 |
| mixed C | Full | 0.778170 | 0.774838 | 0.619159 | 0.768444 | 0.950239 |
| mixed C | Late-weighted | 0.869191 | 0.886907 | 0.788992 | 0.840778 | 0.960085 |
| mixed C | Frozen | 0.389836 | 0.426698 | 0.405168 | 0.265896 | 0.461583 |

Four-case mean scores: **Juqst 1.000000; Paper 0.761903; Full 0.699194; Late-weighted 0.803043; Frozen 0.414675.**

The score amplification is visible even on `single_0`: Paper's nonidentity probability loss is `0.0372870`, while its correlation RMSE is only `0.00468754` and CMI RMSE only `0.0000625882`. Their respective scales are `0.755736`, `0.00296614`, and `0.0000415897`; consequently the same reconstructed-channel change scores `0.952981`, `0.387545`, and `0.399218`. These are not missing components.

## Leave-one-depth predictive evidence

| Acquisition | Policy | Raw RMSE | Projected RMSE | Interior RMSE | Low-order RMSE |
|---|---|---:|---:|---:|---:|
| single | Juqst | 0.003057465 | 0.003062589 | 0.002225883 | 0.008872908 |
| single | Paper | 0.003102157 | 0.003161760 | 0.002502878 | 0.010296883 |
| single | Full | 0.003062729 | 0.003085328 | 0.002172711 | 0.008498910 |
| single | Late-weighted | 0.003067876 | 0.003125466 | 0.002298561 | 0.009269896 |
| single | Frozen | — | 0.003048146 | 0.002096634 | 0.006426097 |
| mixed A | Juqst | 0.051987534 | 0.053524637 | 0.002512171 | 0.060564315 |
| mixed A | Paper | 0.051987599 | 0.053813651 | 0.002522916 | 0.060679859 |
| mixed A | Full | 0.052009152 | 0.053337180 | 0.002486887 | 0.060285289 |
| mixed A | Late-weighted | 0.051992774 | 0.053046077 | 0.002509527 | 0.060438422 |
| mixed A | Frozen | — | 0.052555738 | 0.003691784 | 0.071421593 |
| mixed B | Juqst | 0.052015782 | 0.052573298 | 0.002442339 | 0.055753711 |
| mixed B | Paper | 0.052016210 | 0.052731161 | 0.002455049 | 0.055819965 |
| mixed B | Full | 0.052019619 | 0.052849594 | 0.002414778 | 0.055774278 |
| mixed B | Late-weighted | 0.051998893 | 0.052769619 | 0.002441578 | 0.055437655 |
| mixed B | Frozen | — | 0.052421149 | 0.003753756 | 0.074265703 |
| mixed C | Juqst | 0.054272304 | 0.054486472 | 0.002755312 | 0.056868298 |
| mixed C | Paper | 0.054271721 | 0.054609027 | 0.002771835 | 0.056963534 |
| mixed C | Full | 0.054289020 | 0.054376321 | 0.002708208 | 0.056851760 |
| mixed C | Late-weighted | 0.054257143 | 0.054038961 | 0.002753334 | 0.057211718 |
| mixed C | Frozen | — | 0.054805701 | 0.003930499 | 0.070875002 |

**Do not overinterpret the pooled number.** Pooled projected RMSE is `0.046386942` for Juqst and `0.046160152` for Frozen, superficially favoring Frozen. However, the depth-zero extrapolation fold contributes **99.788–99.821%** of the reference mixed-acquisition squared residual. Frozen has **46.96%, 53.70%, and 42.65% worse interior RMSE**, and **17.93%, 33.20%, and 24.63% worse low-order RMSE**, on mixed A/B/C. Its held-out depth-one projected RMSE is `0.0104958`, `0.0105137`, `0.0110526`, versus reference `0.00681705`, `0.00653287`, `0.00725181`. This is a genuine predictive disadvantage in those views, not proof of an unimplemented diagnostic or a known-physical-channel error. Conversely, Frozen improves the single acquisition's interior and low-order RMSE by **5.81%** and **27.58%**.

The ambiguity control does not share this mixed-data weakness: Full improves interior RMSE on all four acquisitions by **2.39%, 1.01%, 1.13%, 1.71%**, and its largest low-order degradation is just **0.037%** (mixed B). Paper is not universally as good: on single it worsens interior RMSE by **12.44%** and low-order RMSE by **16.05%**. The numerical evidence supports estimator ambiguity, not an assertion that every alternative is equally good.

The JSON includes optimistic independent-shot parity noise scales (`0.000981585` single; approximately `0.00070668` mixed). Acquisition-level sequence variation and correlated modes prevent interpreting these as reliable uncertainty bars. In particular, a depth-zero extrapolation problem should not be equated with a statistically calibrated lack-of-fit test.

## Frozen submission: raw oracle errors versus own-p consistency

Raw losses below are exactly the evaluator's quantities: nonidentity normalized L1; off-diagonal correlation RMSE; CMI RMSE in nats; absolute error in base-two DAG JS distance.

| Acquisition | Probability loss | Correlation RMSE | CMI RMSE | DAG-JSD error |
|---|---:|---:|---:|---:|
| single | 0.0456434701 | 0.00882873984 | 0.0000604496292 | 0.00284625091 |
| mixed A | 0.227896229 | 0.0131746946 | 0.000413097370 | 0.0363850841 |
| mixed B | 0.247731696 | 0.0158441254 | 0.00352117708 | 0.0455684754 |
| mixed C | 0.209452796 | 0.0145596997 | 0.00184224616 | 0.0303031422 |

Own-p consistency instead compares each submitted diagnostic against an independent recomputation from **that same submitted probability distribution**, not the oracle distribution:

| Acquisition | Correlation consistency RMSE | CMI consistency RMSE | DAG-JSD consistency error | Oracle score after diagnostic recomputation |
|---|---:|---:|---:|---:|
| single | 6.55e-18 | 1.37e-16 | 1.90e-15 | 0.565909601299 |
| mixed A | 1.55e-16 | 9.74e-16 | 1.11e-16 | 0.331022786892 |
| mixed B | 1.58e-16 | 9.53e-16 | 0 | 0.371931322039 |
| mixed C | 2.06e-16 | 1.44e-15 | 1.67e-16 | 0.389836061130 |

The largest score change after recomputation is **8.36e-14**. Maximum entrywise submitted-versus-own-p errors across all four acquisitions are `6.94e-16` (correlations), `2.48e-15` (CMI), and `1.90e-15` (JSD). Thus none of the submitted diagnostic losses can be explained by their being omitted or incorrectly calculated on these inputs. A fitting or distribution-estimation weakness remains possible; own-p consistency alone never certifies scientific accuracy.

## Independent validation and author disposition

- Direct categorical joint-table CMI, centered-event covariance, and separately constructed child/parent conditionals agree with reference diagnostics on all 20 reconstructed distributions. Maximum absolute differences: correlation `6.01e-15`, CMI `4.40e-15`, JSD `1.87e-15`. The unnormalized DAG product has mass error at most `2.22e-16`; acyclicity is checked. A separate four-qubit self-check covers unequal categorical cardinalities, empty conditioning, zero variance, and five unreachable parent configurations using fair binary conditionals. Explicit parity summation checks the Walsh transform to `5.55e-17`.
- Independently initialized SciPy bounded two-parameter fits check the profiled scalar optimization for each policy/acquisition. Maximum rate difference is `1.61e-6`; maximum objective difference is `1.86e-14`. These are numerical optimization checks, not evidence that the reference is physical truth.
- **Disposition:** do not accept the observed low score as a new hard scientific task or as four failed pipeline components. Record the substantial fit-policy ambiguity and the submission's specific mixed-data predictive weaknesses separately. The current private-reference agreement objective is not sufficient to adjudicate the former as scientific failure. This is an evidence-based rejection of a false-hardness interpretation, not a claim that the reference is broken or the submission should receive perfect credit.
