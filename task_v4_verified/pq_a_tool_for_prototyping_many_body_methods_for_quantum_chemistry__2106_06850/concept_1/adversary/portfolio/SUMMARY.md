# Private search summary — 2026-08-28

**Superseding follow-up:** `RESPONSE_COMPLETENESS_AUDIT.md` establishes universal
response-family infeasibility for the frozen validator and cases. Its unpruned
graph certificates bound response speedup at 1.022753055829×, below 1.15×, and
reverify without an optimizer. The initial search-only “unknown” assessment
below is retained as historical context, not the latest conclusion.

**No passing solution found. Achievability remains unknown, not impossible.**

All outputs are private to `concept_1/adversary/portfolio/`. Participant, evaluator, original manifest, and tested attempts are not modified; tested attempt contents were not read.

## Frozen 24-case result

- Geometric-mean speedup: **1.291981598239×**, target **1.75×**.
- Worst-family speedup: **1.021440249765×**, target **1.15×**.
- All 24 selected plans pass the exact supplied `contract.validate`; all scratch caps hold.

| Family | Achieved speedup | Integer-certified graph speedup upper bound |
|---|---:|---:|
| left_density | 1.389949414728 | 1.399591608305 |
| linear_response | 1.021440249765 | 1.022753055828 |
| quadruples | 1.306907803559 | 1.309444856478 |
| right_triples | 1.501648887756 | 1.517545633020 |

## Strength and limitations of the search

- Enumerated every factor subset and binary split, merging exact subnetworks under dummy-label renaming, repeated-factor permutation, and output-axis permutation.
- A second graph includes every retained subset of internal summed indices whose array can fit the cap, allowing delayed summations and reuse of those additional networks.
- Global AND/OR LP branch-and-bound selects contraction trees jointly, rather than independently selecting trees and merely caching their coincidences.
- Multi-root coordinate replanning, stochastic amortized-cost tree choices, five output orders, four cache eviction policies, and memory-triggered recomputation are exercised in the forced deep run. Oversized-tree fallback is exercised separately in a targeted audit.
- All 24 achieved costs equal their numerically closed global branch-and-bound optima. Memory-feasible schedules attain those costs; no scheduling/recomputation penalty remains on the selected plans.
- Independent integer-arithmetic checks of LP Lagrangian certificates give an overall **1.298674377957×** speedup upper bound **within the enumerated graph model**. The achieved arithmetic is within **0.518024%** of that conservative relaxed bound.
- LP certificates are checked using integer coefficients, signed integer multipliers, and exact reduced-cost lower bounds on [0,1] variables; floating-point solver status alone is not the certificate.
- Graph enumeration/completeness is not elevated to a universal proof about every legal plan. These are strong scoped negative results, not a declaration that the task is impossible.
- Reaching 1.75× from this portfolio requires another **26.172480%** geometric-mean arithmetic reduction. Response is the strongest observed family bottleneck.

## Validation and runtime

- Hidden generated plans validated: **14452**, invalid candidates: **0**.
- Expanded graph binary operations independently audited as exact contraction plans: **50671**.
- Forced memory-fallback audit: **24** valid plans, **1003** fallback events; no baseline fallback was needed by the winning portfolio.
- The baseline is recomputed on every hidden case and agrees with the frozen manifest; independent graph optima also agree with the baseline before cross-term reuse.
- Cold fresh solver invocations: **75.454095s total**, **7.059751s maximum**, all valid under 30s, one BLAS thread, and a 2 GiB address-space limit.
- Cold runtime checks use local resource-limited subprocesses, not the evaluator bubblewrap sandbox. This portfolio is not presented as a fresh participant attempt.
- Specialized exact-input certificate replay: **6.046631s total**, **0.696067s maximum**. These timings are not offline optimization timings.
- Offline in-process generation seconds by run: `ordinary`=21.565978, `expanded`=61.290134, `deep`=187.513432.

## Additional source-derived challenges

- **32** separate private cases use the provided parser-extracted source terms without invented tensor identities or symmetry assumptions.
- Four dimension/batch/cap settings per family, with uniform random and reuse-rich source-term selections, cover 20–80-term batches (response has at most 34 source terms), 4–20 occupied, and 12–112 virtual dimensions.
- These challenge sets are diagnostic only: they do not replace, tune, or modify the original hidden cases or frozen target.
- Diagnostic overall speedup: **1.853895091936×**; validated candidate plans: **4592**; invalid candidates: **0**.

- Diagnostic family speedups: `right_triples`=2.659483150747×, `left_density`=1.784850948280×, `linear_response`=1.049782119002×, `quadruples`=2.370512501945×. The response-family gate still fails; these diagnostics are not a passing fixed-target portfolio.

## Artifacts

- `solve.py`: runnable input-to-plan optimizer; `replay.py`: clearly marked privileged exact-input certificate replay.
- `best/`: best valid per-case plans, integer lower-bound certificates, and exact aggregate/per-case metrics.
- `per_case_scores.csv`: flop counts, peaks, speedups, per-case generation/cold/replay timings, and scoped bounds.
- `ordinary/`, `expanded/`, `deep/`: separate portfolio reports and every candidate validation record.
- `verification/`, `verification_full/`: independent semantic, baseline, bound, and cold-runtime audit reports.
- `challenge/`: generated source-derived cases, provenance, plans, and scores; `read_only_input_hashes.json`: reproducibility hashes.
