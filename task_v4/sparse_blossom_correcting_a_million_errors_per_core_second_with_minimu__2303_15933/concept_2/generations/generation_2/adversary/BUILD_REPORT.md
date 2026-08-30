# Privileged generation-two construction report

The actual promoted generation-one champion is v_2, after both independent
ultima-alpha attempts passed. It—not the private builder witness—is the
participant baseline. Its first broad calibration replay is preserved in
the parent adversary/V2_STRESS_REPORT.md and v2_stress_report.json.

The ratchet adds explicit exhaustive row/column sign directions, with
continuous amplitude along each. It does not infer a multidimensional box
from corners and does not use hidden random directions. Rate-budget
preservation removes global-noise drift as the explanation for failures.

Private calibration selected 51 local anchors and local targets 0.85 nats,
0.845 posterior, and 0.0000175 syndrome probability. The original global
targets and certificate remain unchanged. The preexisting private known
witness is feasible without a new optimized design search. No private
solver or feasibility artifact is exposed in the public packet.

Known independent score: 1.00573298863178; local bounds: {"certified_gap": 0.8548730403370154, "certified_opposite_posterior": 0.8465519046062109, "certified_syndrome_probability": 1.804021906363681e-05}.

Actual champion generation-two score: 0.939363803021116; nominal score retained: 1.00892989981203. Exact pointwise failure clusters: {"gap": 1, "none": 40, "opposite_posterior": 3}.

All 2,265 points per artifact were independently recomputed by generic
full-state C++ probability/min-plus DP. The reversible GF(2) basis merely
changes state coordinates and processes independent transitions first.
The audit compares all 4,530 outputs against separate frontier inference,
plus brute force, a slow generic full-state check, edge-order invariance,
rank-deficient cases, off-anchor bounds, and malformed artifacts.

Known evaluation CPU/wall seconds: 328.331 / 349.339; peak RSS: 66.016 MiB. Baseline CPU/wall seconds: 312.880 / 322.204.

Frozen at 2026-08-28T17:20:59.833440+00:00, before any generation-two fresh launch. This is
ratchet one of at most three. No further task generation is created, no
runner is launched, and no original frozen participant/evaluator is edited.
