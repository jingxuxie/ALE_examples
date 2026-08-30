# Bounded ratchet review: no promotion recommended

Both original fresh attempts are solved. The higher unrounded v2 result, 1.1245411788778297, is archived with its frozen submission, evaluations, and manifests. Active participant/evaluator/status files remain unchanged; no new fresh model or promotion occurred.

## Actual search evidence

- 23 completed configuration replays, including two n=8 controls: all produced admissible artifacts; 15 pass and eight fail. The two ordinary retained pool alternatives pass at 1.1221797657498267 and 1.1273501422691823. Each control reproduces 1.1245411788778297.
- For `middle_cross_45`, the private witness is 1.094955838159416 at a pre-fixed target 1.09. Every single-family configuration of the actual champion fails; even recombining all 16 output endpoints reaches only 1.0877026333364312. This is a genuine method-level minimax gap, not a path, label, shape, or stale-threshold failure.
- However, a new two-parameter interpolation of champion endpoints passes at 1.094290457685765 in 8.621409096999999 CPU seconds, including its full independent audit. The validated n=8 draft is therefore not recommended as evidence of difficult search. Its target is not raised after this result. The `middle_cross_35` oracle miss is much narrower and is not substituted to manufacture a threshold gap.

## Larger private design

`large_patch_probe/candidate_n24/` contains a reproducible, nonidentical three-band instance, feasible reference, private pair, baseline, independent audits, and a complete frozen artifact checker. All three bands are different, all interband couplings are positive and reciprocal, and the modes do not commute. Integrated total couplings range from 0.22144179345340279 to 2.774296312611569; the equality-constrained space has 504 free coordinates per kernel.

The exact checker confirms private score **1.1219300515770714** at target **1.11**, fixed before replay. Baseline is admissible, score **1.0**, not valid. The signed-frequency matrices are separately assembled for each family, and the regular-row no-go control passes. The private witness checker takes 7.895 CPU seconds with 726096 KiB process-lifetime peak RSS on this run.

The dimension/path-only champion adapter reproduces the n=8 control exactly. On n=24, the coarse SLSQP run logs at least 225 objective calls and reaches a low-endpoint temperature of 80.91891420424972 K, but emits no pair before the **600-second stage cap**. Its empty GNU-time file then triggers a bookkeeping JSON error. The resource reader is hardened without repeating the search; raw logs are preserved in `large_patch_probe/stopped_run/`. Exact search CPU/RSS are unknown, not zero. This is **inconclusive**, not an optimization gap, invalid-input failure, or proof of failure under a one-hour budget. The visible weak-band structure may also allow a faster decomposed search.

## Optional stronger invariants

No Frobenius-moment or isospectral constraint is added, and no witness for that variant is claimed. Such restrictions change the feasible search problem; an old LP step that ignores them cannot count as a challenger failure. A future proposal must first produce a distinct-Tc pair satisfying all strengthened invariants and then test an invariant-aware adaptation of the search. This review does not spend another budget on an unverified construction.

## Available draft and reporting

`participant/`, `input/FORMAT.md`, and `evaluator/evaluate.py` remain a fully validated but **not recommended** n=8 draft for parent inspection. `validation/summary.json` records the exact private/baseline/oracle checks and 17 hostile-artifact/constraint rejection probes. `reporting_only/REPORTING_REGRESSION.json` confirms the reason/core/worst/resource reporting addition preserves the original numerical scores and verdicts. Archived original contracts and outputs are not rewritten.

No search remains scheduled. Only the parent may decide to resume investigation, promote a proposal, or launch a fresh model. The current evidence does not justify claiming that a difficult ratchet survived.
