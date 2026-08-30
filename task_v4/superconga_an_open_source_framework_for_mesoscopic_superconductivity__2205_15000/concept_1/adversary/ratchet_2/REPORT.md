# A2 bounded broad replay: measured disposition

**Status: resource_inconclusive under the predeclared certification policy.**
Two repeatable physical quality gaps remain, so claiming `no_meaningful_ratchet` or global robustness would be inaccurate. The strict quiet-load gate was not met, so no certified generation-3 proposal is created or installed. Main's official A2 result remains valid/pass/core=1.0/worst=1.0.

## Coverage and outcomes

- Preserved 24 validated physical cases and their preexisting attained fields; selected 13 stationary starts with gaps at least 0.5 before reading v2.
- Ran 21 unchanged-solver processes, sequentially: 13 broad cases, two warm-discovery runs, and six frozen-input repeats. All work is stopped; no fresh agents or live asset edits.
- Broad outcomes: 10 valid; eight reach or beat witnesses; two retain stationary/topological gaps; three wrapper deadline failures (`nf04`, `nf05`, `nf06`) are infrastructure, not hard counterexamples.
- 17 harness tests pass, including all 24 reference/physical-input rechecks, gradient/gauge checks, topology covariance, supplied-start equality, safe NPZ loading, result gates, and control decisions.

## Persistent quality findings

| Case | Supplied A2 baseline B | Preexisting witness W | Gap | Three frozen warm-repeat scores |
| --- | ---: | ---: | ---: | --- |
| vp03 | -1422.745156445820 | -1423.947169760779 | 1.202013314959 | 0, 0, 0 |
| vp05 | -1497.639653053848 | -1498.186104051798 | 0.546450997951 | 0, 0, 0 |

Both cases are in the real `vortex_pinning` family. Fields are stationary, unchanged under warm replay, and improve by less than 1e-9 under tighter local polishing. Reliable topology diagnostics find 148 and 114 changed vortex plaquettes relative to the respective witnesses (plus one changed hole winding in vp03). No new witnesses, synthetic frustrations, or global-minimum assertions are used.

## Root cause versus resource caveat

All six scored repeats are resource-valid and finish in 10.02–20.72 seconds. The captured solver declares 55 seconds and its largest time-cutoff reserve is 6.5 seconds. Trusted outer timings bound the remaining internal budget below by at least 34.27 seconds; therefore these failures cannot be explained by hitting a search time guard. Independent initialization-only reproduction succeeds. The solver logs zero nonlinear candidate trials: its harmonic hole-sector search has no explicit bulk-vortex relocation proposal, while the private witness changes the vortex allocation. This is evidence of a representation/search limitation, not loose tolerance or a larger grid alone.

Nevertheless the frozen *proxy* for clean-load certification requires CPU/wall >=0.95, sibling busy fraction <=0.30, and low initial core load. No repeat meets all three. We do not silently substitute the stronger fixed-work argument for that predeclared gate. Exact resource counters and all six fields are preserved; `quality_counterexamples.json` makes this distinction machine-readable.

Three other cases exceed wrapper deadlines with shared-workspace scratch. Solver-printed energies are not trusted or counted as passing results. Payload CPU accounting is unavailable when the protected monitor is killed; raw outer Bubblewrap CPU is not a payload measurement. A local-scratch correction was requested, but no out-of-scope scratch writes or additional campaign were performed without permission.

## Handoff

- `report.json`, `status.json`: full measured disposition; `quality_counterexamples.json`: exact baseline/witness paths, zero scores, topology, and budget-independence argument.
- `source_manifest.json`, `submission`: four-file byte-preserved finished v2 artifact; `provenance/v2_exit.json`, `v2_evaluation.json`, and `v2_audit.json`: official completion evidence.
- `corpus/manifest.json`, `policy.json`: frozen 24-case preservation, 13-case selection, immutable preexisting witnesses and resource/quality gates.
- `runs`, `controls`, `frozen_warm_inputs`, `diagnostics`: all per-process logs, timings, checked fields, fixed starts, and polish/topology controls.
- `root_cause.json`, `root_cause.py`: successful 15-/20-dimensional sector initialization checks, not a new optimization portfolio.
- `validation.json`, `physical_revalidation.json`, `test_harness.py`: 17 passing tests and 24-case physical/reference validation.

No generation-3 executable is claimed feasible, no ground state is asserted, and no next generation is installed. Main may review the fixed-work evidence or authorize normal local ephemeral scratch for a bounded instrumentation repair before deciding on any proposal. Durable writes remain exclusively in ratchet_2.
