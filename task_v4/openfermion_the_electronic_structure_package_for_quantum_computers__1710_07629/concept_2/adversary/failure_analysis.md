# Bounded posthoc failure analysis

Only the two scored cutoff artifacts are analyzed. No fresh attempt, optimization,
ratchet, or participant/evaluator/status edit was performed.

## Outcome and shared bottleneck

Both submissions are **valid and accurate on all four targets**, but certify only
2/4. Core/worst-family scores are **0.5/0.5** for each; secondary resource scores
are 0.9352941 (v1) and 0.9654655 (v2). All projector errors are below 8.46e-15;
this is not an accuracy, ill-conditioning, parser, or missing-dependency failure.

| Target | Gate/depth caps | v1 gates/depth | v2 gates/depth |
|---|---:|---:|---:|
| ladder_14 | 32/10 | 34/9 — fail | 32/10 — pass |
| ladder_16 | 36/11 | 35/9 — pass | 37/9 — fail |
| irregular_16 | 40/12 | 50/15 — fail | 45/12 — fail |
| irregular_18 | 44/13 | 39/12 — pass | 38/13 — pass |

The shared **irregular_16** miss is substantive: v1 exceeds the gate cap by
**10 (25%)** and depth by **3 (25%)**; v2 meets depth exactly but exceeds the gate
cap by **5 (12.5%)**. The private witness achieves **38/11**, so feasible recovery
is demonstrated, not conjectured. Both agents also find fewer-gate irregular_18
circuits than the planted 42-gate witness: they are not merely reproducing it.

Main's privileged portfolio takes ladder_14 from v2, ladder_16 from v1, and both
irregular cases from v2. It certifies **3/4**, worst-family **0.5**, resource
**0.9722222**, and still fails irregular_16. This is not a third fresh attempt.
Sources: `attempts/v_1.evaluation.json`, `attempts/v_2.evaluation.json`,
`adversary/fresh_portfolio/report.json`, and `adversary/empirical_decision.json`.

## Different search emphases

**v1: template sparsification plus exact spectral construction.** Its brick
search randomizes three-edge-color layer patterns, applies analytic-gradient
L-BFGS-B sparsity penalties, prunes, and polishes. A separate relaxed constructor
finds connected-subset projector eigenvectors near eigenvalues 0/1, eliminates
them along randomized trees, and accounts for occupation-bitstring transport.
The cutoff actually selects `irregular_16_relaxed.json`; the other selected
circuits come from brick/reduction candidates. Evidence:
`attempts/v_1/brick.py:35`, `attempts/v_1/brick.py:54`,
`attempts/v_1/relaxed.py:11`, `attempts/v_1/relaxed.py:54`, and
`attempts/v_1/final_collect.log:1`.

**v2: gauge-invariant fitting and explicit topology repair.** It minimizes
occupied-frame overlap with the target vacant subspace using analytic Jacobians
and adjoint gradients, avoiding a fixed occupied-orbital gauge. Its search combines
sparse fitting, insertion/removal with nonlinear refits, phase-aware three-gate
turnovers, and depth-constrained expansion. The selected irregular_16 artifact is
`irregular_16_expanded_shallow.json` (45/12). A late pruning run fits 44 gates only
to error 4.64e-4; at 40 gates its best logged 12-layer search error remains about
**0.03044**, far from 1e-8. This is a local search outcome, not a lower bound.
Evidence: `attempts/v_2/optimize.py:29`, `attempts/v_2/optimize.py:119`,
`attempts/v_2/search.py:85`, `attempts/v_2/expand.py:25`,
`attempts/v_2/turnover.py:34`, `attempts/v_2/assembly.log:3`, and
`attempts/v_2/last_i16.log:1`.

These mechanisms and exact, much-shorter-than-baseline outputs demonstrate real
continuous and discrete synthesis work. The remaining failure is simultaneous
native-edge sparsity and scheduling, not failure to understand Gaussian states.

## Cheap redundancy checks

Reevaluation reproduces both saved scores and cutoff hashes. On irregular_16,
all **95 individual gate deletions** were simulated without refitting. The best
remaining projector errors are **0.0318632** (v1) and **0.00902349** (v2): none
passes. There are no identity gates at 1e-12 and no same-edge neighboring pairs
even after commuting intervening disjoint gates. ASAP rescheduling preserving
shared-mode order still requires **15** and **12** layers. Thus ordinary cleanup
does not explain the miss; more complicated identities or reoptimization remain
possible. No submission code was executed and no new circuit artifact was saved.

## Validity and limits

- Launch records report fresh ephemeral, initially empty outputs, read-only task
  access, and unchanged participant/evaluator hashes. Recorded audits deny the
  specified private reads. This is supporting evidence, not a new security audit.
- v1 hits the one-hour timeout; v2 exits normally at about 3593.6 seconds. Recorded
  cutoff captures precede their deadlines by about 23.8/21.0 seconds. Both live
  final solution hashes equal the scored snapshots; unsaved or later work is not
  credited. The JSON records exact cutoff hashes and times.
- Selected source-candidate JSON matches every cutoff circuit. Source/log snippets
  nevertheless do not establish the provenance of every optimization step.
- Two runs of one model on four fixed targets support bounded empirical difficulty,
  not a universal hardness theorem or gate-minimality claim. Both share tooling
  and objectives despite different search emphases. The private witness establishes
  achievability; the privileged portfolio is not independent participant evidence.

The main status `hard_verified_achievable` is consistent with this bounded evidence;
no target, budget, scoring, or status change is proposed.
