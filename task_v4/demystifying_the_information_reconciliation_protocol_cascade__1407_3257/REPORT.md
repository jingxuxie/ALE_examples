# Empirical hardness decision

**Selected task: concept 2, generation 2 — `hard_verified_achievable`.**
Solvability is demonstrated by a private certificate accepted by independent
replays; neither of two isolated one-hour challengers produced a valid witness.

## Concepts, modes, and scores

| Concept | Verification mode | Baseline / champion | Fresh-agent result on retained generation | Ratchets | Final status | Solvability |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Adaptive Cascade under uncertain QBER | A: baseline improvement | Reference cost ratio 1.0; improvement 0% | 11.30% overall improvement, but 1.53% worst-family improvement; fixed targets 8% and 3%. Reliability gates pass. | 0 | `hard_open_candidate` | Unknown |
| 2. Activated fixed-shuffle residual trap | B: counterexample | Baseline 0; generation-1 champion 1; private generation-2 certificate 1 | Two independent scores: 0 and 0. One admissible input leaves no residual errors; the other attempt produces no witness. | 1 | `hard_verified_achievable` | Demonstrated |
| 3. Parity-invisible residual-channel diagnosis | E: active experiment design | Original baseline 80/180; original champion 180/180. Retained baseline 75/180; parameterized champion 161/180 and 166/180 on independent confirmations. | 161/180 (89.44%); worst cell 15/20 (75%), below fixed 171/180 and 18/20 targets. Resource validity 100%; 438.88 mean parity queries. | 1 | `hard_open_candidate` | Unknown |

All six fresh attempts use `ultima-alpha`, a fresh ephemeral context, only
read-only participant assets plus an initially empty writable output directory,
and a 3,600-second development limit. The first tournament solved concepts 2
and 3; their successful submissions were archived before ratcheting. Concept 1
and the final concept-3 challenger used the full limit and left valid artifacts.

## Counterexample and adversarial searches

- **Concept 1:** a private 27-policy portfolio finds no qualifying policy.
  Its completed development evaluation improves overall cost by 18.90% but
  bandwidth cost by only 1.50%, and fails the conditional-stress gate. The
  bounded hidden portfolio run does not complete; no passing result is claimed.
- **Concept 2:** 107 champion-portfolio runs cover 17 private deployment cases.
  The selected case has zero successes in 20 runs, including eleven 240-second
  confirmations. Mechanical dimension adaptations and easy controls rule out
  a stale-size-only failure. The private witness has 24 initial errors, six
  initially odd roots, six corrected bits and 18 residual errors under both
  correction priorities. Independent implementations agree on 8,128 small-frame
  replays and accept the certificate; six malformed artifact fixtures fail.
- **Concept 3:** parameterized-champion searches cover seven contamination
  levels and three query budgets. Original-control behavior is exactly
  reproduced on all 180 transcripts. The retained generation changes only
  contamination to 1/8, 1/6 or 1/4, with unchanged budgets and targets. Independent
  confirmations score 161/180 and 166/180 without resource violations. Failure
  clusters involve component acquisition, contaminated neighborhood selection,
  and finite-sample inference; no passing policy is known at the retained target.

## Substantive capabilities not achieved

- **Concept 1:** uniform cross-regime schedule improvement, rather than an
  aggregate gain that sacrifices bandwidth and short-frame objectives.
- **Concept 2:** low-weight discrepancy construction across overlapping parity
  partitions while preserving activated Cascade residuals under both priorities.
- **Concept 3:** noise-robust sequential topology identification and uncertainty-
  aware allocation of a fixed parity-experiment budget.
