# Supplementary diagnosis of the official E fresh-v1 failure

**The official score is unchanged.** This is a private, post-completion diagnostic, not a new generation, fresh attempt, retest that replaces the official score, or feedback to the fresh agent.

## Official failure and directly observed mechanism

The frozen program scored mean log-RMSE **0.05593327143062893** and worst regime/family log-RMSE **0.13307673088502028**, failing fixed limits 0.055 and 0.095. The failing cell is `chain_hooks/bulk`; every other cell is at most 0.0641068. Runtime was valid.

An unmodified isolated replay of `chain_hooks_0` exactly reproduces its official metrics. An additional trace wrapper runs the frozen source inside the same isolated worker, never in the simulator process, and reproduces the entire query/observation transcript and final estimate exactly.

- `chain_hooks_0` contributes **81.52%** of the official chain/bulk squared error.
- Its channels **07 and 13** contribute **99.19%** of that episode's bulk squared error, or **80.86%** of the whole failing cell's squared error.
- They have identical primary/alternate detector masks `[12, 6]` and the same exposure sector 0. They are not exactly unidentifiable: known action-specific exposures/mixing distinguish them. Under the realized allocation their true-rate local Fisher correlation is **-0.9796**.
- True rates `[0.01079250, 0.01724413]` are estimated as `[0.01570201, 0.00981435]`: opposite log errors **+0.37494 / -0.56363**. This is unstable separation of an aliased pair, not general underestimation of all bulk channels.
- The pair's log-rate contrast error is **0.93856** versus local Fisher SD **0.43501** (about **2.16** local SDs). Its sum has much smaller log error, **-0.09419**. This supports a contrast/aliasing diagnosis rather than missing the overall fault activity.

## What the frozen algorithm actually did

The source optimizes the mean of four predicted family RMS errors (`attempts/v_1_frozen_submission/solution.py:90` and `:102`), not the scored worst-cell guardrail. It uses a 910-shot effective pilot, then 2,500 and 9,000 additional shots, then the final 27,590 shots (`:194`, `:200`, `:246`). The last design is fixed from the estimate at 12,410 shots, without further refitting during that allocation.

The initial pair estimates move along the weakly constrained contrast. At 12,410 shots the two log errors are -0.3654/+0.1546; after the final allocation the ML errors reverse to +0.4205/-0.6264. The final plan predicts per-episode bulk SD 0.09172 at its estimated parameters; evaluating information at the true parameters under the realized allocation gives 0.12171. The robust reference's realized allocation gives 0.10666 for this episode and pair-contrast SD 0.36205 instead of 0.43501. These are post-hoc local design diagnostics, not scored cell RMSEs or proof of a causal allocation effect.

**Posterior averaging did not create the error.** It reduces this episode's bulk RMSE from **0.268256** to **0.240308**, with effective importance sample count **189.81** (fallback threshold 30). Three independent fits using the trusted likelihood, started at bounds midpoint, a fixed random point, and the candidate's pre-posterior estimate, recover the same ML point within **1.14e-5** in every log rate. There is no evidence here of solver nonconvergence or posterior fallback as the cause.

## Three predeclared supplementary noise tapes

Each tape uses all **12 original hidden parameter instances**. Only simulator sampling seeds differ. Each policy/episode uses a fresh, independent writable runtime copy with source SHA verified before and after; the original bubblewrap evaluator, API, 40,000-shot budget, 64-query cap, and 60-second CPU cap are unchanged. No candidate code is imported by the evaluator. Both policies receive only the public spec and observed syndromes.

| Tape | Candidate mean / worst | Meets original limits on this tape | Robust reference mean / worst | Meets original limits on this tape |
|---|---:|:---:|---:|:---:|
| tape_1 | 0.046963 / 0.069299 | Yes | 0.047893 / 0.069205 | Yes |
| tape_2 | 0.049863 / 0.093281 | Yes | 0.049302 / 0.059376 | Yes |
| tape_3 | 0.047807 / 0.061681 | Yes | 0.050873 / 0.066750 | Yes |

Candidate chain/bulk cell errors on tapes 1–3 are **0.063396, 0.071254, 0.061681**. The specific official worst-cell failure recurs in **0/3** replays. Full-suite limits are met by the candidate in **3/3** and the robust reference in **3/3** supplementary tapes. All 72 replay episodes are valid; maximum candidate/reference CPU is **3.1913 / 5.0133 seconds**.

## Interpretation and limits

The official failure is a real, exactly reproducible error concentrated in a noisy, strongly anti-correlated bulk-rate contrast. The supplementary tapes test whether that particular failure repeats; they do not invalidate the original result or demonstrate a systematic population-wide bulk bias. Three noise tapes on fixed parameters are too few to infer a reliable failure probability, establish a general performance ranking, or guarantee future success.

Seeds are paired by tape/episode, but adaptive configurations and query grouping differ between policies; their observations are not identical or shotwise coupled. Fisher inverse calculations condition on realized allocations and are asymptotic/local, so the standardized contrast is not a calibrated p-value. The trace confirms this particular posterior step helped, not that its approximation is exact. No controlled allocation ablation was run, so the role of the mean-risk objective and point-estimated late design is supported descriptively, not established as a sole cause.

`manifest.json` records all sampling seeds before replay and hashes the frozen code, original result, participant, and evaluator. `analysis.json` contains channel-wise errors, pair contrasts/correlations, allocation vectors, traces and optimizer checks. `tape_*_report.json` contains the supplementary full-suite reports; `transcripts/` and `workspaces/` retain private evidence. No files outside `adversary/` were edited, and no fresh feedback or new generation was produced.
