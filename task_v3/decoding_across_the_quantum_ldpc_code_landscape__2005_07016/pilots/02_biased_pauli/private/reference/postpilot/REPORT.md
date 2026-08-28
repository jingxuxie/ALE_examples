# Bounded postpilot audit: reject pilot02 as a remaining HARD gap

## Recommendation

**Reject; do not construct a ratchet or holdout from this audit.** The unchanged
submission implements both central mechanisms and substantially outperforms
the applicable frozen official reference on the existing challenge split.
There is no measured, systematic reference-success region or meaningful
source-existing central mechanism still missing from the submission.

This conclusion does not assert optimal decoding or that every logical
failure is unavoidable. It says the remaining failures do not justify this
source-grounded HARD concept after the bounded pilot round.

## Execution and scores

The supplied model-run duration was 2884.82 seconds; no model was rerun here.
The existing `evidence/fresh_pilot.json` records mean 1.104093567251462,
worst family 1.0, and consistency 1.0. Its bytes were preserved.

This audit ran all four **existing** challenge cases, once, through the
unchanged `private/evaluator.py::main` and existing `isolation.run_submission`.
It used a byte-identical snapshot of `attempt/` beneath this directory to
prevent any submission-side build/cache writes to the protected original.
Only temporary-storage location and retention of returned answer bytes were
instrumented. No scoring formula, limits, report-path contract, environment
inside the isolated process, input, truth, anchor, or solver code was changed.
The prior orchestration report-path error is infrastructure, not a solver
failure; the new report is correctly inside this pilot.

- Challenge `mean_core`: **1.2933691256449589**; `worst_family`: **1.0**.
- Syndrome consistency: **1.0**, all 1024 shots.
- Submission raw logical success: **892/1024 = 0.87109375**.
- Frozen reference raw logical success: **755/1024 = 0.7373046875**.
- Submission CPU: **89.88 s total**, maximum **43.28 s per case**.
- Wall: **114.14937 s total**, maximum **43.90165 s per case**.
- Peak RSS: **37,492 KiB** (about 36.61 MiB).
- No timeout, nonzero exit, CPU-budget violation, or malformed answer.

| Family | Submission success | Reference success | CPU s | Wall s | Peak RSS KiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| lp416_hadamard_x | 256/256 = 1.00000000 | 256/256 = 1.00000000 | 4.68 | 26.20209 | 35076 |
| lp416_clifford_joint | 174/256 = 0.67968750 | 101/256 = 0.39453125 | 41.24 | 42.21164 | 35648 |
| lp882_hadamard_z | 256/256 = 1.00000000 | 256/256 = 1.00000000 | 0.68 | 1.83399 | 36272 |
| lp882_clifford_joint | 206/256 = 0.80468750 | 142/256 = 0.55468750 | 43.28 | 43.90165 | 37492 |

CPU, not wall time, is charged. The first case's approximately 21.52 seconds
of additional wall time is not decoding hardness. Reference CPU values in
`analysis.json` are historical generation measurements; source peak memory
was not recorded and is reported as unknown, not guessed.

## Paired reference/submission outcomes

Success is the existing full logical-coset test, including syndrome validity,
not equality to a sampled error or particular correction.

| Family | Both succeed | Reference only | Submission only | Both fail |
| --- | ---: | ---: | ---: | ---: |
| lp416_hadamard_x | 256 | 0 | 0 | 0 |
| lp416_clifford_joint | 101 | 0 | 73 | 82 |
| lp882_hadamard_z | 256 | 0 | 0 | 0 |
| lp882_clifford_joint | 140 | 2 | 66 | 48 |
| Total | **753** | **2** | **139** | **130** |

The submission gains a net 137 shots, or 13.3789 percentage points. The
reference has no family-level advantage. The 2-versus-139 discordant pairs
give a descriptive exact paired two-sided p-value of about 7.18e-39; this is
not used to validate an outcome-selected subgroup or predict unseen regimes.

## Complete reference-only analysis

Every shot is retained in `shot_diagnostics.csv`; `reference_only.csv`
contains **all two** reference-only wins, not selected examples. Define
`delta = log P(reference correction) - log P(submission correction)` using
the actual independent-across-qubits, joint-four-Pauli channel. Positive
delta means the reference representative has greater likelihood. This is
not an exact logical-coset posterior ratio.

Both wins are in lp882_clifford_joint, case_03.npz; shot indices are zero-based.

| Shot | Joint delta, nats | Independent-marginal delta | Canonical Y-load z-score | Total-error-load z-score |
| --- | ---: | ---: | ---: | ---: |
| 128 | -0.05098122 | +9.34590826 | -0.24341 | +0.34008 |
| 179 | +0.19769123 | -1.65357000 | +0.44269 | +0.95021 |

- **Shot 128: no reference representative-likelihood advantage.** The
  submission's wrong-coset correction is slightly more likely under the
  actual joint channel. Marginal scoring would prefer the source answer,
  but restoring marginal independence is not a defensible general fix.
- **Shot 179: a small correlation-dependent candidate-ranking opportunity.**
  The correct source representative has a 0.198-nat advantage that reverses
  under marginal scoring. This is compatible with finite candidate-search
  limitations, not an absent correlation mechanism: the submission already
  propagates and ranks with the full joint channel. Retained outputs do not
  identify the exact internal search branch or prove per-shot budget exhaustion.

Neither is an extreme correlated-error-load case. Exact logical-coset masses
were not computed; a lower-cost representative is not a proof of a better
coset posterior. One near-tied win of each type is not a systematic region.

For contrast, **all 139 submission-only wins** have a more likely submission
representative, with log-likelihood advantages between 21.62 and 95.43 nats
(mean 54.94). These large measured advantages oppose a missing-correlation
claim much more strongly than the two source-only near ties support one.

## Naturally hard tail versus source-success region

Before inspecting per-shot outcomes, the analysis fixed load bins at +/-1
standard deviation from the known channel expectation. All family/bin cells
for canonical Y count and total Pauli weight are recorded in `analysis.json`.
No thresholds were optimized for reference wins.

For the two correlated families together, the total-error-load partition is:

| Load bin | Shots | Reference only | Submission only | Both fail |
| --- | ---: | ---: | ---: | ---: |
| Below -1 standard deviation | 72 | 0 | 7 | 0 |
| Within +/-1 standard deviation | 360 | 2 | 116 | 72 |
| Above +1 standard deviation | 80 | 0 | 16 | 58 |

Thus the heavier-error tail is genuinely harder, but it is **not** a region
the source can recover and the submission cannot. It has zero reference-only
wins and 58 shared failures. No recorded family/load bin has more reference-
only than submission-only wins. Across all 130 shared failures, the submission
representative is more likely in every case; five pairs are in the same wrong
logical coset, and 125 are in different wrong cosets. These are not hidden
reference successes and cannot justify selecting lucky source outputs.

## Mechanism and source audit

The original public NumPy baseline uses independent component marginals and
a linear-syndrome solve; original native binary BP+OSD was also supplied.
The completed submission is not that baseline with a superficial wrapper:

- `attempt/solve.py:33` transports the full four-outcome channel and corrections
  through every local frame and qubit permutation.
- `attempt/decoder.cpp:40` stores four-state channel costs.
- `attempt/decoder.cpp:167` combines both syndrome sectors in four-state
  posterior costs and remarginalizes them into messages; X/Z correlation is
  propagated, not discarded.
- `attempt/decoder.cpp:346` performs reliability-ordered recovery, while
  `attempt/decoder.cpp:540` uses a bounded multi-schedule candidate ensemble
  and selects with the joint channel likelihood.
- `attempt/decoder.cpp:76` performs stabilizer-preserving descent. Exact
  coset-posterior summation is absent, but it is also absent from the frozen
  source reference; it cannot serve as a source-existing withheld mechanism.

The applicable reference remains the original frame adapter and unmodified
official `css_decode_sim` conditional component update with BP+OSD-CS(10).
No new stronger solver, tuned source variant, task, channel regime, ratchet,
holdout, or fresh-model run was created. Given the measured source disadvantage
and mechanisms already present, an additional slower-source search was not
justified for this bounded audit.

## Integrity and artifacts

`hashes_before.json` and `hashes_after.json` cover the participant, entire
attempt, challenge corpora and anchors, evaluator, shared/local isolation
helpers, source snapshots and original matrix files, and existing source
adapter/provenance documents. They match. The evaluated snapshot also matches
the original attempt byte-for-byte, including the native library.

- `solve.py`: `9465e0d95f71b964a16d5b1aec882fae0572b206123f1b21dcfb8e5ddc79419b`
- `decoder.cpp`: `e669d30a6fb8536d17563732b6e36f3f31ef542ae53b45b3c9cbec9f492648b1`
- `decoder.so`: `1cc6ae9ebb46a0239f6f3242bbf2b3dea6b5e19113e063226b9c53d754cc00ef`

All additions are below `private/reference/postpilot/`: the audit driver and
analysis script; this report; score, integrity, execution, and analysis JSON;
the two diagnostic CSVs; four retained prediction archives; and the untouched
submission snapshot. `artifacts.json` enumerates the complete added-file list.

The bounded isolated run command is `python -B .../postpilot/run_audit.py`
with the usual outer-sandbox approval. It refuses to rerun after producing
the challenge report. `python -B .../postpilot/analyze.py` only reanalyzes the
retained predictions. Main remains responsible for tournament reconciliation
and the final outcome report.
