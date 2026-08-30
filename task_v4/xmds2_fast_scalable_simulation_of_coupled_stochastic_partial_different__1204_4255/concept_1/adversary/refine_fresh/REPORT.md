# Privileged fresh-A refinement evidence

Generated 2026-08-28T05:03:28.309070-07:00. Writes are confined to `concept_1/adversary/refine_fresh/`. No fresh agents were launched; original attempts, participant, evaluator, hidden cases, and status were not edited.

## Fixed target and conclusion

Generation-1 target is unchanged: overall `1 - geometric_mean(cost / baseline_cost) >= 0.20`, every family >= 0.08, all 30 hidden instances within 120 seconds on one CPU and 1 GiB aggregate address space. Hidden baseline total remains 345617.

**No passing planner found. Achievability remains unknown, not disproved.**

The resource-tested generic bundle scores **18.069245% core, 9.349567% worst family**, total cost **283699**, versus baseline **345617**; wall **84.387 s**, CPU **66.957 s**, sampled aggregate AS **76.34 MiB**, sampled aggregate RSS **61.23 MiB**. All 30 answers pass the exact public checker.

## Actual original-pair portfolio

`fresh_pair/solve.py` actually reruns both independently rebuilt fresh planners on every supplied instance, verifies each plan, and selects the lower cost, with baseline fallback. It is not an offline per-case schedule selection.

Measured **17.999229% core, 9.321016% worst family**, cost **284084**, wall **71.027 s**, CPU **36.311 s**, aggregate AS **73.00 MiB**. Complementarity is real but insufficient for the fixed 20% overall target.

The main-reported official fresh scores were v1 core 0.1728140863 / worst 0.0917104841 / runtime 19.47 s and v2 core 0.1798711714 / worst 0.0932101553 / runtime 13.28 s. Those are main-provided context, not results of this harness. Time-bounded search can produce slightly different schedules under host contention.

## Search and cost-only evidence

Reviewed both fresh Python and C++ sources before execution; copied only relevant sources and rebuilt our own binaries. Searches tested original modes, larger forward/reverse beams, separate widths and horizons, memoized pair roots, optional reverse merges, forward-guided reverse estimates, triple-root merging, graph search, rollout search, reverse heuristic scales, and generic runtime portfolios. All configurations and outcomes, including timeouts, are in `VARIANTS.tsv` and `results/*.json`.

The exact-checked per-instance oracle union of completed valid experiments reaches **18.091034% core, 9.349567% worst family**, cost **283626**. This is cost potential only: it combines saved experimental schedules and is not a runtime-compliant submission or hidden-case lookup permitted in a submission. Even this union falls below 20%.

Native modes with no internal deadline may time out; those failures are retained, not assigned scores or treated as passing potential. Concurrent offline tuning ran on separate pinned CPUs. High wall/CPU ratios reflect host contention; measured timeouts do not prove a configuration intrinsically needs that much CPU. Only the explicitly recorded real wrapper executions establish measured portfolio resources.

## Portable bundle and reproducibility

Copy only `candidate/` for submission. `solve.py` uses `/task/workspace/model.py`, bundles the unchanged public baseline, reads generic configurations, launches sequential native searches, and selects minimum exact-checked cost. No IDs, family labels, hidden inputs, baseline-cost table, or saved schedules enter this bundle. Its global planner deadline is 109 seconds with baseline fallback. The source is included beside its rebuilt binary. `candidate/README.md` gives the rebuild and launch commands; `bundle_manifest.json` hashes every packaged file.

Generation-only hidden access was used to tune generic configurations and measure scores. The surrounding directory contains privileged cases/results and must not be copied into a participant environment.

Reproduce locally with `PYTHONDONTWRITEBYTECODE=1 python3 measure.py candidate_specs.json` from this directory. CPU 198 is the authoring host affinity used in that spec; select an available CPU if replaying elsewhere. `pair_specs.json` runs the original-pair bundle. `summarize.py` rechecks stored valid plans against the exact checker. `choose_portfolio.py` performs offline configuration selection; that selection is not itself runtime proof.

## Resource and audit scope

The direct wrapper tests pin the process tree to one CPU, apply an inherited 1 GiB RLIMIT_AS, and sample summed child/parent virtual and resident memory plus affinity at 25 ms intervals. The monitor kills on expanded affinity, aggregate-AS overflow, or 120-second wall timeout. Startup of the outer tool namespace is excluded; Python parsing, baseline planning, child launches, and candidate verification are included. CPU totals include waited-for descendants. Sampling is not an official isolation certificate; the hardened evaluator remains authoritative.

This follow-up did not modify or rerun the root evaluator. The main-reported one-CPU/aggregate-AS hardening is respected; historical audit observations from the preceding sidecar are not reasserted as current vulnerabilities. No new evaluator flaw was established in this refinement. All scored generated answers pass exact action legality, stale-version, pinned-home, and memory checks implemented by the current public checker; that statement is not a new independent malformed-input audit or Fourier semantic proof.

## Exact measured variants

| Variant | Valid | Core % | Worst % | Cost | Wall s | CPU s | AS MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| candidate_actual | yes | 18.069245 | 9.349567 | 283699 | 84.387 | 66.957 | 76.34 |
| collapse_once256 | yes | 17.989814 | 9.249833 | 284117 | 24.200 | 20.726 | 79.58 |
| fresh_pair_actual | yes | 17.999229 | 9.321016 | 284084 | 71.027 | 36.311 | 73.00 |
| graph128_expand4000 | no | — | — | — | 120.500 | 64.850 | 137.72 |
| guide_collapse_half | yes | 17.893006 | 9.217892 | 284635 | 22.608 | 16.668 | 49.67 |
| guide_full | yes | 17.633517 | 9.322799 | 284946 | 17.301 | 14.981 | 52.58 |
| guide_half | yes | 17.924508 | 9.349567 | 284523 | 28.600 | 13.887 | 52.88 |
| opt_balanced512 | yes | 18.016664 | 9.200171 | 283942 | 36.038 | 28.660 | 85.36 |
| opt_collapse128 | yes | 17.866312 | 9.239180 | 284387 | 23.348 | 20.909 | 68.79 |
| opt_collapse256 | yes | 17.828666 | 9.239180 | 284606 | 44.737 | 33.336 | 85.49 |
| opt_mode25 | yes | 18.022217 | 9.321016 | 283951 | 39.644 | 31.384 | 278.46 |
| opt_wide1024 | yes | 17.792746 | 9.321016 | 284851 | 60.040 | 41.164 | 131.50 |
| quick_reverse_h16 | yes | 17.865079 | 9.253386 | 284372 | 36.082 | 6.747 | 14.37 |
| quick_reverse_h2 | yes | 14.337334 | 8.806419 | 296323 | 23.925 | 6.660 | 15.42 |
| quick_reverse_h200 | yes | 17.609380 | 9.349567 | 286518 | 10.732 | 7.197 | 14.21 |
| quick_reverse_h8 | yes | 17.342401 | 9.187777 | 286344 | 23.005 | 5.999 | 13.96 |
| quick_reverse_scale075 | yes | 17.767991 | 9.342425 | 285365 | 9.729 | 7.884 | 14.82 |
| quick_reverse_scale2 | yes | 16.629877 | 9.184237 | 288654 | 10.111 | 6.736 | 13.44 |
| reverse_horizon100 | yes | 17.942902 | 9.321016 | 284447 | 25.834 | 19.556 | 54.20 |
| reverse_only1024 | yes | 18.058093 | 9.349567 | 283826 | 96.817 | 54.735 | 43.23 |
| reverse_only1024_h200 | no | — | — | — | 120.511 | 6.641 | 33.66 |
| reverse_only256 | yes | 17.949872 | 9.321016 | 284202 | 9.738 | 7.609 | 16.11 |
| reverse_only4096 | no | — | — | — | 121.470 | 39.458 | 164.72 |
| reverse_scale_half | yes | 17.593810 | 9.248057 | 285200 | 25.227 | 16.873 | 43.40 |
| rollout_forward32 | yes | 17.427722 | 9.126804 | 285590 | 28.869 | 13.110 | 188.95 |
| triple_collapse256 | yes | 17.580545 | 9.244506 | 285268 | 63.698 | 10.176 | 77.56 |
| triple_reverse512 | no | — | — | — | 120.253 | 7.971 | 26.12 |
| v1_original | yes | 17.131703 | 9.171048 | 286346 | 26.377 | 19.222 | 10.54 |
| v1_wide2 | yes | 17.432215 | 9.249469 | 285820 | 49.865 | 46.053 | 12.02 |
| v2_mode25 | yes | 18.022217 | 9.321016 | 283951 | 37.040 | 30.719 | 278.46 |
| v2_mode25_width256 | yes | 18.036102 | 9.335286 | 283908 | 108.673 | 98.206 | 704.87 |
| v2_original | yes | 17.975772 | 9.321016 | 284155 | 15.127 | 12.889 | 51.30 |

## Hidden-set family scores for actual selected bundle

- `layout_pressure`: 24.300044%
- `mixed_anisotropy`: 22.353236%
- `shared_bases`: 16.375890%
- `unequal_fields`: 9.349567%
- `version_epochs`: 17.145824%

## Public examples

The same portable candidate passed 10/10 public example checks in 41.967 seconds wall. Evidence: `public_validation.json`; this is an exact-checker smoke test, not an additional official resource certification.

Protected hidden-case SHA-256: `858d8151987928148f391888c7d5175e3ad20437aabc4d1b8f9fc00dae0eb164`.
