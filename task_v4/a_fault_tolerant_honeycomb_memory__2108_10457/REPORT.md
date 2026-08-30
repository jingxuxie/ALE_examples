# Hardness-discovery report

## Concepts and verification modes

| Concept | Primary verification mode | Final status |
|---|---|---|
| 1: Circuit-level correlated decoding | A: baseline improvement | solved |
| 2: Dense heralded-erasure honeycomb design | C: witness/design construction | hard_open_candidate |
| 3: Held-out paper experiment prediction | D: hidden prediction | solved |

## Baseline, champion, and fresh-agent scores

- Concept 1: baseline family-balanced/worst failure ratios 1.000000 / 1.000000; fresh champion 0.530711 / 0.814721. Lower is better; targets 0.80 / 0.95 were met.
- Concept 2 nominal generation: identity baseline core/worst 0.277778 / 0.050781; fresh champion 0.996528 / 0.980469, passing.
- Concept 2 retained dense generation: supplied champion baseline core/worst 0.837402 / 0.479492. Fixed targets remain at least 0.85 / 0.60, across 36,864 hidden supports.
- Concept 2 independent fresh attempt `v_2`: core/worst 0.841471 / 0.498535; valid, not passing; 3600.1 seconds of the one-hour allowance.
- Concept 2 independent fresh attempt `v_3`: core/worst 0.841471 / 0.498535; valid, not passing; 3431.3 seconds of the one-hour allowance.
- Concept 2 private portfolio best: core/worst 0.841471 / 0.498535; not passing.
- The first dense fresh artifact is exactly reflection-equivalent to the supplied champion. Independent bidirectional response-space checks establish equal IID population performance; its small finite-sample score gain is not a genuine robustness improvement.
- Concept 3: baseline core/worst 0.749702 / 0.367130; fresh champion 0.948889 / 0.896356. Worst-score target at least 0.50 was met.

## Counterexample search results

- Concept 1: 98,304 additional source-native shots across 12 broader cases. Champion balanced/worst failure ratios 0.702678 / 0.887906; maximum request time 54.674 seconds. No violation of the fixed target.
- Concept 2: broad physical erasure sweeps isolated the dense-IID failure regime; 27 exact flagged-support fault combinations have zero syndrome and nonzero logical action. Three 300-second private search seeds plus 2,420 structural candidates screened (12 finalists fully scored) produced no passing dense design.
- Concept 2: independent 32,768-support worst-group confirmation gives the first dense attempt 0.484039 correctability, with a 99% Wilson interval [0.476932, 0.491153], well below 0.60. This is post-submission validation, not a new scoring condition.
- Concept 3: finer distance stratification of all 692 held-out observations gives worst score 0.828217, with 0 factor-two residual failures after accounting for count uncertainty. No justified further ratchet was found.

## Ratchets, final status, and solvability

- Ratchet generations: concept 1 = 0; concept 2 = 1 (two total task generations); concept 3 = 0. The two dense attempts are replications of the same frozen generation, not successive ratchets.
- Retain concept 2 generation 2 as `hard_open_candidate`. Solvability is unknown; no dense-generation passing construction is known, and no impossibility proof is claimed.
- Concepts 1 and 3 are `solved`; their fresh executable champions demonstrate achievability. Nominal concept 2 was also solved but does not demonstrate dense-generation solvability.

## Substantive failed capability

Construct a static local-Clifford supercell that improves dense heralded phase-erasure correctability while preserving all four logical Pauli coordinates across all three sizes; the 24-qubit, 0.32-density group remains the substantive bottleneck.
