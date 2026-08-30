# Concept 3 preparation: held-out finite-size prediction

Date: 2026-08-28. Status: recommendation only; awaiting agreement before implementation.

## Recommendation

Choose D: predict logical-failure probabilities at unobserved code sizes and physical-noise rates from the paper's recorded Monte Carlo experiments. This is empirical simulation data, not hardware data. Keep the circuit, decoder, observable, and prediction target fixed. The scientific challenge is finite-size/noise extrapolation and probability calibration, not improving a decoder, finding a counterexample, reproducing a source formula, or predicting a fitted teraquop number.

This recommendation is conditional on a closed-data evaluation contract. The original labels are public. Removing them from a local training file does not make them secret from an internet-enabled contestant or eliminate possible pretraining contamination.

## Direct artifact audit

The v2 ancillary CSV was downloaded into memory and parsed directly; no CSV copy was written into shared authoring.

```text
source: https://arxiv.org/src/2108.10457v2/anc/honeycomb_memory_stats.csv
bytes: 146922
sha256: 64fad935bfdbf8846cb68c4f3289860b34c50856ee8006f7e53672bcac1884ab
upstream commit: d71737d3b4fb8878e856f8bd66b9632cc7078159
```

The CSV has 1,724 rows, version 2 throughout, 247 zero-failure rows, and no duplicate full experiment keys. Its fields are:

```text
data_width,data_height,rounds,noise,circuit_style,preserved_observable,
code_distance,num_qubits,num_shots,num_correct,total_processing_seconds,
decoder,version
```

| Circuit style | Rows | Proposed use |
| --- | ---: | --- |
| honeycomb_EM3_v2 | 300 | Primary |
| honeycomb_SD6 | 294 | Primary |
| honeycomb_SI1000 | 278 | Primary |
| surface_SD6 | 300 | Primary |
| surface_SI1000 | 300 | Primary |
| honeycomb_PC3 | 252 | Excluded from the initial benchmark |

The five primary styles give 1,472 rows and ten style/decoder families. Decoders are `internal` and `internal_correlated`; observables are H/V for honeycomb and X/Z for surface. The honeycomb distances are 4, 8, 12, 16, 20; surface distances are 3, 7, 11, 15, 19. Every primary row has `rounds = 3 * code_distance`. Physical-noise values are:

```text
0.0001, 0.0002, 0.0003, 0.0005, 0.0007,
0.001, 0.0015, 0.002, 0.003, 0.005,
0.007, 0.01, 0.015, 0.02, 0.03
```

There are 28 absent primary-grid configurations, all at honeycomb distances 16/20 and noise >= 0.007. Do not fill them with synthetic labels. The smallest shot count among primary rows is 16; 277 primary rows have empirical failure fraction above 0.5. Treat these as noisy finite-sample observations, not impossible records.

PC3 has a separate noise constructor, is absent from the main paper collection list, and its threshold plotting entries are commented out. Do not relabel it as the paper's EM3 or pool its observations with EM3_v2. Its missing configurations and model interpretation would need a separate scope decision.

## Fixed target and semantics

For each query, predict the probability `q` that the supplied decoder fails the preserved observable over the entire supplied memory experiment. The grader uses `failures = num_shots - num_correct`. This is a scalar probability, not the integer failure count and not its logarithm.

The raw CSV rate is per complete 3d-round experiment. The paper's plots convert it to a d-round code-cell rate. Under the homogeneous independent-cell parity model, that conversion is `q_cell = (1 - (1 - 2*q)^(1/3))/2` for `q <= 0.5`; it is not `q/3`. Avoid this modeling assumption in the target by grading raw experiment probabilities. A code-cell conversion may be a clearly labeled diagnostic, not the ground truth.

Keep the two observables separate. Their marginal failure counts do not establish a measured joint logical failure probability. Do not grade teraquop extrapolations, a fitted threshold, or paper line-fit outputs as if they were measured labels.

The paper used adaptive sampling: roughly 100 million shots, 1,000 failures, or evidence of near-50% failure, with batching and distributed overshoot. Thus test `num_shots` and runtime are outcome-dependent side channels, not legitimate query features. Keep both private.

## Proposed metadata-only split

Apply the same configuration split simultaneously to every decoder and both observables. A block key includes geometry, rounds, noise, and circuit style but excludes decoder/observable. Aggregate any repeated records before splitting; none were found in this CSV.

Define small sizes as honeycomb d <= 12 and surface d <= 11; large sizes are honeycomb 16/20 and surface 15/19. Define low noise as exactly 0.0001 or 0.0002. These boundaries do not depend on model predictions or per-row outcomes.

| Partition | Configuration region | Rows | Zero-failure rows | Rows with >= 100 failures |
| --- | --- | ---: | ---: | ---: |
| Public training | Small sizes, p >= 0.0003 | 780 | 12 | 506 |
| Hidden size extrapolation | Large sizes, p >= 0.0003 | 492 | 101 | 174 |
| Hidden noise extrapolation | Small sizes, p in {0.0001, 0.0002} | 120 | 30 | 60 |
| Hidden upper-bound diagnostic | Large sizes, p in {0.0001, 0.0002} | 80 | 76 | 0 |

Training has exactly 78 rows in each of the ten style/decoder families. Each noise-extrapolation family has 12 rows. Size-extrapolation families have 38, 44, 46, or 52 rows, depending on missing configurations.

The primary hidden score uses 612 rows: size plus noise extrapolation. The deepest joint extrapolation region must remain a separately reported upper-bound diagnostic: 76 of its 80 rows have no failures and no row has 100 failures. It cannot support claims of accurate ultralow-rate point prediction. Zero-failure cases remain in the primary partitions too; do not drop them, turn them into zero-probability truth, or choose individual test rows by their error counts.

This diagnostic-only decision follows a disclosed author-side coverage audit, not a baseline performance search. Freeze the manifest before model comparison; do not alter it to make a tested agent fail.

Use public rolling-origin development folds inside the 780 training rows: honeycomb 4/8 -> 12 and surface 3/7 -> 11 for size, and p >= 0.0007 -> {0.0003, 0.0005} for low-noise extrapolation. Preserve decoder/observable blocks in those folds too. Select model complexity on these folds, then refit all public training data. These folds are development data, not independent hidden tests.

## Transparent family-worst score

Let `n_i` be hidden shots, `k_i` hidden failures, and `q_i` the submitted probability. Define the per-row likelihood deviance:

```text
D_i = 2 * [k_i * log(k_i / (n_i*q_i))
           + (n_i-k_i) * log((n_i-k_i) / (n_i*(1-q_i)))]
```

Use the exact limiting value zero for a term with zero count. Reject nonfinite/out-of-range predictions; apply a published numerical clip to [1e-12, 1-1e-12] for valid boundary probabilities. For zero failures this reduces to `-2*n_i*log(1-q_i)`, retaining genuine upper-bound information without an arbitrary pseudocount in the grading labels.

For each of the ten fixed style/decoder families and each of the two scored stress types, first average deviance within each observable, then average the two observable means. The primary loss is the maximum of these 20 predeclared cell losses. Lower is better. Report all 20 cell losses and the overall mean alongside it. If the framework requires a higher-is-better scalar, publish the monotone map `score = 1/(1 + primary_loss)`.

This uses measured evidence strength through `n_i`, without letting the number of rows or the easier families dominate the score. Do not silently divide by shots or change weights after seeing test results. It is a likelihood-based fit loss, not a fixed-n chi-squared significance test. Under a parameter-independent stopping rule, the stopped-sequence likelihood retains the `q^k*(1-q)^(n-k)` factor, but ordinary fixed-sample confidence claims are not automatically justified. The worst-cell aggregate is a robustness objective; do not advertise it as a strictly proper aggregate scoring rule.

Do not bootstrap decoder/observable rows as independent experimental blocks when reporting uncertainty. The public aggregates do not establish independent provenance between all related rows.

## Baseline implementation proposed after agreement

Use a small standalone Python/NumPy count-likelihood regressor, not an import of the paper's plotting/decoding code. NumPy is present in `authoring/deps`; the dependency inventory identifies version 2.2.6. No new decoder, large model download, simulation, or internal binary is necessary for CSV prediction.

For each style/decoder/observable stratum, fit a saturating model:

```text
features = [1, standardized_distance, standardized_log_noise,
            standardized_distance * standardized_log_noise]
q = 0.5 * sigmoid(features @ coefficients)
objective = sum(-k*log(q) - (n-k)*log(1-q)) + ridge_penalty
```

All feature normalization is fitted on training data. Use deterministic initialization, damped optimization with a bounded iteration count, and a fixed ridge grid selected only on public rolling-origin folds. Binomial-count fitting retains zero-failure evidence. A Jeffreys pseudocount may be used for initialization only, not as the grading truth. Keep the baseline's saturation at 0.5 separate from the prediction protocol, which need not assume a perfect decoder.

The eventual CLI should consume a labeled training CSV plus a metadata-only query CSV and emit exactly `query_id,p_failure`. Verify ID coverage, probability finiteness, deterministic repeated runs, and absence of hidden file access before publication. Add a constant-0.5 negative control and a simple log-linear distance-fit comparator to demonstrate that the task is not solved merely by replaying a paper fit.

Candidate improvements can address finite-size corrections, low-noise effective-distance crossover, threshold transition shape, and shared structure across observables/decoder families. The paper notes different effective-distance behavior for EM3, so a single universal power law is not established truth. Whether these refinements produce a challenging, learnable score gap is unmeasured until a train-only pilot is approved.

No baseline has been implemented, run, timed, or scored in this preparation. No tested agent was launched. Do not describe the dependency inventory or the CSV audit as a baseline success test.

## Leakage and validity gates

1. Give contestants only public training counts and whitelisted query configuration fields: geometry, rounds, physical noise, circuit style, observable, code distance, qubit count, decoder, and an opaque query ID. No test shots, correctness counts, runtime, zero-event flags, stopping flags, or outcome-dependent filters.
2. Keep all decoders and observables of a physical configuration on the same side of every split. Rebuild opaque IDs independently of original row numbers. IDs alone do not protect publicly identifiable configurations.
3. Keep the full original CSV, original PDF/figures, upstream archives containing data, stored predictions, and fit products out of the contestant filesystem and retrieval context. A sanitized source-only simulator can be supplied if desired; it must not include target-bearing artifacts.
4. Disable contestant network/retrieval access to the public CSV and task-authoring files. A policy sentence without filesystem/network enforcement is not a leakage defense. Use an author-only ground-truth location and a separate restricted grader process.
5. Freeze source hash, whitelist, all split blocks, clipping, score aggregation, baseline-selection folds, and any acceptance bar before final agent evaluation. Never use hidden labels for baseline hyperparameter selection.
6. Label this honestly as a controlled public-data holdout, not cryptographically secret or provably contamination-free data. If the evaluation setting requires genuinely unpublished labels or permits arbitrary web research, a CSV-only final test does not meet that requirement.
7. For genuinely unpublished labels, discuss a fresh fixed-decoder source-native simulation design instead. That could remain D with hidden new measurements, or become E with a bounded experiment budget. Neither can claim to reproduce the paper's internal correlated decoder: that binary was not released. Using a modern open decoder creates a new explicitly versioned target and requires separate agreement, runtime/noise-precision checks, and training data consistent with that target.

## Primary references and local source anchors

- arXiv:2108.10457v2, Section 4 and Figure 5: 3d simulated rounds and d-round reporting; Figure 6: finite-size line fits and effective-distance caveat; Appendix C: CSV, stopping behavior, and unreleased correlated decoder.
- `authoring/upstream/src/collect_data.py:276`: `ShotData`; `num_errors` at line 282 and raw logical rate at line 311.
- `authoring/upstream/src/collect_data.py:344`: recorded-data parser and aggregation.
- `authoring/upstream/src/plotting.py:11`: experiment-to-code-cell conversion.
- `authoring/upstream/src/paper/main_collect_all.py:141`: noise grid; decoders at line 158; honeycomb configuration grid at line 163.
- `authoring/upstream/src/noise.py:36`: distinct PC3 constructor; EM3_v2 at line 63.
- `authoring/upstream/src/paper/main_render_threshold_figure.py:74`: commented-out PC3 plot cases.

## Next decision

Agree on controlled-data D, the 780/612/80 split, and the raw-probability/worst-cell score before building. Then implement only the agreed concept-owned benchmark, baseline, and leakage checks; do not modify concept_1, concept_2, or shared authoring without further authorization. This preparation creates only this note.
