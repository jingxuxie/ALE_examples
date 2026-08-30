# Private champion search sidecar

## Frozen script and main-owned execution

Frozen unchanged on **2026-08-28**, with SHA-256:

```text
01d15c2074606c7e111a20588a9f1f0ba0398d7f2a6c9005bd473a19e130ca78  search_champion.py
```

Main reports generation 1 officially passed: mean NRMSE **0.0359657**, worst-family **0.0571207**, **32/32 valid**. Main owns the authorized search with `--submission champions/generation_1 --episodes 128 --jobs 8 --seed 930817326 --repeat-worst 24 --fisher --output-dir adversary/champion_search_1`. **Do not start a duplicate sweep.** The builder has not executed this champion. Static, unconfirmed source hypotheses are recorded separately in `champion_failure_hypotheses.md`; they are not search results.

Run **only after the main session authorizes a completed submission that passed the full frozen evaluator**. This script does not run a fresh agent, modify a target, construct a new suite, or decide a ratchet. Keep the champion and every generated artifact private. Use an immutable, self-contained directory under `champions/` or a dedicated `/tmp` snapshot; submissions under `adversary/` are rejected, matching the official evaluator's private-path restriction.

From `concept_3`, after authorization:

```sh
python3 adversary/search_champion.py --submission champions/generation_1 --episodes 128 --jobs 8 --seed 7836419 --repeat-worst 12 --fisher --output-dir adversary/search_7836419
```

The output directory must be new and disjoint from the mounted submission and public/evaluator directories. The four **exact public family laws** generate balanced, independently seeded points, shuffled before screening. For nonmultiples of four, counts differ by at most one. Parameter seeds, screening noise seeds, and three independent repeat seeds per point are fixed before executing anything; no frozen evaluation episodes are read. `--repeat-worst N` screens all points, excludes infrastructure failures, then repeats the worst N parameter points under **three fresh noise seeds**, excluding the selecting observation from the robust summary.

Workers use a persistent **spawn process pool**, never a thread-pool `preexec_fn`. Every strategy episode still starts a new bwrap namespace using the trusted helper with `ready_marker=True`, then the frozen `runtime.run_episode(..., startup_handshake=True)` protocol, shot/query limits, and resource caps. Parent-side worker code never imports submission code. Limits: 1–512 points, 1–8 workers, at most 64 repeated points, 90-second sandbox startup and 20-second solver time per episode, plus a default 900-second global execution deadline (`--max-wall-seconds`, maximum 3600). On cancellation/deadline the pool is terminated; bwrap's parent-death handling kills its isolated descendants. Completed JSONL records remain available. The same pool serves screening and repeat phases.

Outputs are `manifest.json` (settings and source/submission hashes), `points.json` (private parameters and seeds), streamed `screening.jsonl` and `repeats.jsonl`, and `report.json` (family summaries, robust cases, heuristic clusters, and optional Fisher diagnostics). Submission hashes are checked again afterward. Incomplete runs, changing submissions, and infrastructure failures must not count as hardness evidence.

Clusters separate repeatable invalidity, stable wrong-frequency/axis candidates, nuisance precision, and failures not reproduced above the diagnostic cutoff. They are **heuristics, not causal diagnoses**; three repeats are limited evidence, not a statistical guarantee. The reference cutoff 0.09 is not a new per-episode acceptance criterion. Optional `--fisher` computes only the fixed baseline schedule's nuisance-inclusive local rank/CRLB, flagging poor information for that design—not fundamental unidentifiability or an adaptive lower bound. There is no true-parameter oracle strategy and no automatic case promotion.

Permitted infrastructure smoke test, without executing a champion:

```sh
python3 adversary/search_champion.py --submission participant/baseline --episodes 2 --jobs 2 --seed 827531 --repeat-worst 0 --output-dir /tmp/cr_search_smoke_NEW
```

## Completed builder smoke evidence

Exactly that **two-episode public-baseline** smoke test ran with two spawned workers and seed `827531`: **2/2 valid**, **zero infrastructure errors**, **8.9181 seconds** wall time, and unchanged submission hashes. Mean NRMSE was `0.1169158111` (aliasing `0.1518432584`, near-degenerate `0.0819883638`); these test the harness, not the champion. Evidence is retained at `/tmp/cr-sidecar-check.WamKVJ/results/report.json`, alongside its manifest and streamed records. No repeat or champion strategy execution was performed by the builder. Non-executing checks also passed for deterministic balanced draws, distinct noise streams, reference-schedule budget, synthetic repeat clustering, full-rank local Fisher calculation, and frozen scientific source/data hashes.

Recheck resource-only candidates at lower concurrency before attributing them to estimator design: eight-worker contention can trigger the champion's internal time guards even when every episode is protocol-valid. Three fresh-noise repeats reduce screening-selection bias but do not establish a causal mechanism or eliminate ordinary precision limits.
