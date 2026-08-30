# Hardness-discovery report

## Concepts and verification modes

| Concept | Primary mode | Ratchet generations | Final status | Solvability |
|---|---|---:|---|---|
| 1. Loss-resilient quantum characterization allocation | A — baseline improvement | 2 | `hard_open_candidate` | unknown for the retained target |
| 2. Phase-robust coherent-leakage counterexample | B — counterexample/falsification | 1 | `solved` | Demonstrated by isolated fresh agents |
| 3. Finite-shot quantum-memory prediction | D — hidden prediction | 0 | `solved` | Demonstrated by a data-only fresh learner |

Three concepts were built from ten considered concepts. Six isolated `ultima-alpha` attempts used a one-hour limit each.

## Baseline, champion, and fresh-agent scores

Pairs in the score columns are **core / worst-family**. Generations 0 and 1 of concept 1 use fractional risk reduction; generation 2 uses champion-intact risk divided by submitted worst-three-loss risk. Concept 2 scores are absolute prediction-probability gaps, but every physical/calibration/leakage constraint must also pass.

| Concept / generation | Supplied baseline | Fresh score | Fresh result |
|---|---|---|---|
| 1 / 0 | 0 / 0 reduction; mean intact risk 13.203226 | 0.642889 / 0.614003 | Passed; became champion 1 |
| 1 / 1 | 0 / 0 reduction; mean two-loss risk 528.085560 | 0.979995 / 0.567266 | Passed; became champion 2 |
| 1 / 2 | 0.00007734 / 0.00003338 | 0.199817 / 0.166386 | Valid; failed fixed 0.25 / 0.20 targets |
| 2 / 0 | 0.007782 / 0.007476; insufficient gap | 0.104700 / 0.100911 | Passed all five scenarios |
| 2 / 1 | 0.104700 / 0.092328; fails calibration/leakage constraints | 0.088588 / 0.078705 | Passed all 21 scenarios |
| 3 / 0 | RMSE 0.162195991 | RMSE 0.000535494; worst family 0.000727309 | Passed every predictive target |

The retained attempt reached the 3,600-second cutoff with a valid design. Its intact-risk ratio was **1.189170**, within the 1.20 guard; it used exactly **1,600,000 ticks and 24 circuits**. Its mean three-loss risk was **24.816579**, or **5.004591×** champion-intact risk instead of the allowed 4×. Its worst-regime inflation was **6.010131×** instead of 5×.

## Counterexample-search results

- **Concept 1, first ratchet:** loss of two selected records exposes severe information concentration in the original champion. A 3,000-point private sweep supports the loss-resilience successor.
- **Concept 1, second ratchet:** the two-loss champion remains effective for its original contract, but three losses raise its mean risk from **4.917090 intact to 100,059.914230** over 3,000 operating points. An independent 600-point sweep gives **112,359.172180**. The dominant triple removes nearly all Y-gate z-axis sensitivity in 2,616/3,000 points; secondary failures affect the X gate's z-axis sensitivity. Additional boundary tests and independent dense/rank-update checks corroborate the mechanism. The new generation explicitly requires three-loss usability rather than merely halving a nearly singular baseline's risk.
- **Retained-attempt confirmation:** a disjoint 600-point ensemble scores **0.197061 / 0.158410**, with intact ratio **1.185149**; it also fails. No target changed after launch.
- **Concept 2:** independent phase drift defeats the first champion; a bounded uniform-rescaling search finds no repair for the selected ±0.008-radian case. The next champion survives **18,849 grid/random scenarios plus 4,948 evaluations in 60 local searches** inside the unchanged uncertainty box. Independently reproduced extrema and rounding tests reveal no genuine further failure. This is finite evidence, not a whole-box proof.
- **Concept 3:** **12 campaigns, 48 devices, and 98,304 held-out queries** reveal no substantial champion failure. Worst campaign RMSE is **0.000652007**, worst family **0.000887839**, and worst device/family cell **0.001048889**. No scientifically justified successor was selected.

## Solvability and final decision

**Retain concept 1, generation 2, as `hard_open_candidate`.** The fresh score falls **20.07%** below the fixed core target and **16.81%** below the worst-family target. This is a substantive quality failure, not malformed output, unavailable software, or an acquisition-budget violation.

The current-generation private search scores **0.069844 / 0.039421**, with intact ratio **1.200097**; it does not pass. Two other static design artifacts from the completed fresh attempt also fail. **Solvability of the retained target remains unknown; no impossibility claim is made.** Passing designs for earlier generations do not establish this target's achievability.

The substantive capability missed is **constrained, loss-resilient experimental design meeting simultaneous average and worst-regime information-retention requirements without sacrificing normal-operation efficiency**. Both counterexample construction and finite-shot prediction were solved and are not retained as hard tasks.
