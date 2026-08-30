# Privileged sidecar result

**No passing planner or passing schedule collection was found. Fixed-target
solvability remains unknown.** Neither the 20% overall target nor the 8%
per-family target was changed. The best generation-only schedules reach
**16.318515% overall**, with **8.625633% worst-family reduction**. Thus the
family requirement is met but the overall requirement is not.

All changes and generated evidence are confined to `concept_1/adversary/`.
Participant/evaluator/hidden/status files and active trials were not modified.
No fresh agents were run, and no main-tournament attempts were inspected.

## Exact hidden30 results

The frozen baseline is re-run and checked, matching **345,617** total cost.
Every reported selected plan is accepted by the unchanged exact checker.
Percentages below are geometric-mean cost reductions, not reductions of the
sum of costs.

| Planner/evidence | Total cost | Overall | Worst family | Wall seconds | CPU seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| 12 weighted-reuse policies, direct constrained run | 302,677 | 12.385213% | 5.574564% | 7.736 | 3.816 |
| Compact shortest-route cache beam portfolio | 296,340 | 14.011776% | 7.699832% | 47.641 | 47.146 |
| Compact anchor/waypoint beam plus weighted policies | 293,052 | **15.414716%** | **8.501216%** | **70.903** | **67.303** |
| Larger 66-policy/three-beam portfolio, offline | 295,780 | 14.146177% | 7.851948% | 210.316 | 208.964 |
| Width-128 future-waypoint beam, offline | 289,903 | 15.966185% | 8.461722% | 470.240 | 469.375 |
| Width-64 common-mask anchor beam, offline | 291,184 | 15.724535% | 8.551482% | 228.763 | 228.142 |
| Best schedule per case across all completed runs | **289,095** | **16.318515%** | **8.625633%** | Not a timed submission | See below |

The direct runs process all 30 instances in one process, explicitly pinned to
one CPU with 1-GiB `RLIMIT_AS`, 120-second CPU and wall limits, and single-thread
library environment settings. The strongest timed planner peaks at **19,896 KiB
RSS**. These are real generic stdin/stdout planners, not hidden-case lookup.

**The direct timing runs are not official isolated evaluations.** They do not
include bubblewrap startup, and their reports explicitly record
`network_isolated: false`. No official isolated pass or portable passing bundle
is claimed. Since no candidate met the cost threshold, none was promoted to a
portable submission for the official evaluator. The user-reported namespace
startup cost must still count against 120 seconds in such an evaluation.

The best-of schedule collection is **privileged, generation-only evidence**.
Its five completed offline searches consumed about **1,076.344 CPU seconds**
in aggregate, before the separately timed compact runs. Saved schedules do not
turn this search into a runtime-compliant or generalizing submission. They
establish the stated achieved costs, not a 20% passing construction and not an
impossibility bound.

## Family details

| Family | Compact anchor planner | Best privileged schedules |
| --- | ---: | ---: |
| shared_bases | 13.290594% | 14.249771% |
| layout_pressure | 19.048030% | 20.971784% |
| unequal_fields | 8.501216% | 8.625633% |
| version_epochs | 15.685039% | 15.981907% |
| mixed_anisotropy | 20.042267% | 21.126299% |

## Search methods

`privileged_planner.py` implements weighted marginal transform-reuse eviction,
respecting each field's next version invalidation. The portfolio varies the
future-use decay, duplicate-use weighting, size normalization, and marginal
versus absolute value. It chooses schedules using actual checker cost.

The cache-state beam enumerates inclusion-minimal eviction sets, keeps valid
in-place/out-of-place action histories, deduplicates cache states, and uses
discounted future transform savings to rank the beam. Additional route variants
visit upcoming requested representations. The anchor variant also proposes
mask intersections/unions and useful layouts from near-future requests, so it
can retain intermediates not themselves requested. Neither family labels nor
hidden IDs are supplied to or used by the streaming planners.

The compact anchor entry point uses the 12-policy portfolio and a width-16,
local-width-4 beam with one future waypoint plus candidate mask/layout anchors.
Larger widths and lower-heuristic variants were also measured, without reaching
the fixed overall target. No optimality or exhaustive-search claim is made.

## Trusted checker and audit evidence

See `AUDIT.md` for reproducers, qualifications, and suggested repairs.

- **55/55** malformed/stale/home/memory expectation tests pass; no semantic
  schedule-validation bypass was found in this finite suite.
- Independent FFT/IFFT and physical-layout replay passes **3,000 tiny reads**
  and all **1,774 reads** in the best hidden schedules. Recomputed costs and
  scratch peaks agree exactly with the checker. Maximum hidden Fourier error
  is approximately **1.776e-14**.
- The actual evaluator raises uncaught `RecursionError` for deeply nested JSON.
- A protocol-conforming 30-home-read, zero-cost instance raises uncaught
  `ZeroDivisionError` rather than receiving the specified ratio 1. Supplied
  hidden30 baselines are positive and unaffected.
- The actual privileged bubblewrap probe exposes **384 CPUs** to both parent
  and child. Its address-space/CPU limits are per-process, not an aggregate
  job-memory or one-CPU restriction. This is distinct from filesystem/network
  isolation; no destructive resource stress test was performed.

The protected model, baseline, protocol, evaluator, and hidden case hashes still
match the audit snapshot and the initial read. Hidden cases SHA-256:

`858d8151987928148f391888c7d5175e3ad20437aabc4d1b8f9fc00dae0eb164`

Best schedule JSONL SHA-256:

`b0ab362183bda226ae40118177e77fe8129211efaa3f7092c5e22a2875b1a968`

## Artifact map

- `best_privileged.json`: exact per-case/family results, selected source runs,
  independent replay results, resource classifications, and protected hashes.
- `best_privileged.plans.jsonl`: 30 actual schedules, in hidden case order.
- `runtime_anchor.json`, `runtime_anchor.plans.jsonl`: strongest directly
  resource-verified generic planner, including all exact per-case costs.
- `runtime_compact.json`, `runtime_level1.json`: other constrained measurements.
- `search_*.json`, `search_*.plans.jsonl`: complete offline run evidence and
  schedules; all reported costs are rechecked by `collect_evidence.py`.
- `anchor_planner.py`, `compact_planner.py`, `privileged_planner.py`: streaming
  planner code; the last file also has privileged offline measurement modes.
- `search_beam.py`, `verify_runtime.py`, `collect_evidence.py`: reproduction and
  validation drivers.
- `audit_checker.py`, `audit_results.json`, `zero_cost_case.json`: checker and
  evaluator robustness/numerical evidence.
- `probe_resources.py`, `resource_probe/solve.py`,
  `resource_probe_results.json`: actual runner resource observations.
- `manifest.json`: hashes and sizes of the final sidecar files.

Do not mount this entire generation-only directory into a participant trial:
it intentionally contains privileged schedules and scores. A future portable
bundle must contain only the generic planner code and required public/baseline
dependencies, with `/task/workspace` imports and bundled baseline source as
requested, never the private evidence files.

## Reproduce

From this directory, using the supplied Python 3.10 environment (NumPy 1.21.5,
SciPy 1.8.0 available; the planners themselves use the standard library):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 verify_runtime.py --anchor
PYTHONDONTWRITEBYTECODE=1 python3 verify_runtime.py --compact
PYTHONDONTWRITEBYTECODE=1 python3 verify_runtime.py --level 1
PYTHONDONTWRITEBYTECODE=1 python3 privileged_planner.py --measure --level 3 --output search_level3.json
PYTHONDONTWRITEBYTECODE=1 python3 search_beam.py --width 128 --local-width 8 --scale 3 --waypoints 3 --output search_waypoints.json
PYTHONDONTWRITEBYTECODE=1 python3 search_beam.py --width 64 --local-width 6 --scale 3 --waypoints 1 --anchors --output search_anchors.json
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 collect_evidence.py
```

Offline commands intentionally exceed participant time limits. All measurement
and evidence outputs remain under this directory. The conclusion is unchanged:
**trusted improvement evidence, but unknown fixed-target solvability**.
