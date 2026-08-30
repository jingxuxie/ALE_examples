# Predict larger, quieter quantum memories

Fit a predictor of logical failure probability from the recorded Monte Carlo experiments supplied in `input/train.csv`. Predict every configuration in `input/queries.csv`, including larger code distances and physical-noise values absent from training. This is prediction of a fixed decoder's performance, not a decoder implementation or a new circuit design.

## Interface

Submit a directory containing `solve.py`. The evaluator runs:

```text
python solve.py TRAIN_CSV QUERY_CSV OUTPUT_CSV
```

Write UTF-8 CSV with exactly the header `query_id,p_failure` and exactly one row per query, in any order. Probabilities must be finite numbers in `[1e-15, 1-1e-15]`. No extra columns or IDs. The output is a probability, not a failure count, log probability, per-round rate, or code-cell rate.

`TASK_ROOT` points to this participant directory. `workspace` contains NumPy; system SciPy is also available. The process has 120 seconds, 2 GiB address space, no network, read-only participant/submission access, and a writable temporary working directory. Only the participant tree and your submission are contestant materials. Do not retrieve the original public data or use precomputed held-out labels. No particular model, method, ablation, or report is required.

Run the starter outside evaluation with:

```text
PYTHONPATH=workspace python baseline/solve.py input/train.csv input/queries.csv predictions.csv
```

## Data and target

Each record specifies geometry, rounds, physical noise, circuit/noise style, preserved observable, nominal code distance, qubit count, and decoder. Training additionally includes shot counts and correct-decoding counts: failures equal `num_shots - num_correct`. Query IDs are opaque.

Predict the probability that the named decoder fails the named observable over the **entire experiment**. Every experiment lasts `3 * code_distance` rounds. Do not divide by rounds or combine the two observables. The original observations use adaptive stopping, so query shot counts and runtimes are deliberately withheld. A zero-failure training row is finite evidence for a small probability, not proof of probability zero. Small samples may have observed failure fractions greater than one half.

The five styles are honeycomb EM3_v2, SD6, SI1000 and surface SD6, SI1000, each with internal and internal-correlated decoders. Honeycomb observables are H/V; surface observables are X/Z. PC3 is not part of this task.

Training has 780 rows: honeycomb distances 4/8/12, surface distances 3/7/11, and physical noise at least 0.0003. Queries comprise 492 larger-distance cases at those noise values, 120 small-distance cases at noise 0.0001/0.0002, and 80 joint large-distance/low-noise diagnostics. Both observables and both decoders of a physical configuration stay together across every split. Missing source configurations are not synthesized.

All tuning must use public training labels; final evaluation is not a development oracle.

## Fixed evaluation

The grader uses actual hidden counts, independent of the starter's predictions. For each row it constructs the probability interval whose Bernoulli count likelihood is at least 1/1000 of the maximum likelihood. This is a **likelihood-support interval**, not a claimed 95% confidence interval under adaptive stopping.

The row error is the distance in log10 probability to that interval, zero inside it. A zero-event row imposes only an upper constraint. Within each style/decoder/stress cell, average squared errors separately for each observable, then average the two observable means and take the square root. The primary loss is the worst of the 20 fixed cells: ten style/decoder families times size/noise extrapolation. Score is `10 ** (-primary_loss)`; higher is better.

Success requires score at least **0.5**, equivalently worst-cell RMS log10 error at most `log10(2)`. This allows a factor-two residual multiplicative discrepancy after statistical uncertainty, in every family/stress cell. The 80 extreme joint cases are reported separately and do not change success: most cannot resolve an ultralow point probability from their observed counts. Full scoring constants are in `input/protocol.json`.

Evaluator results include `core_score` (macro-cell RMS accuracy transformed by `10**(-loss)`), `worst_family_score` (the primary score), `runtime_seconds`, `runtime_score`, `resource_score`, `valid`, `passed`, and `reason`. Runtime/resource score is `max(0, 1-runtime_seconds/120)` for valid executions, zero for invalid ones; the 2 GiB memory limit is enforced rather than reported as a measured peak. Runtime score does not change the fixed quality target. Invalid executions or outputs have zero scores and `passed: false`.
