# Final hardness-discovery report

**Final status: `hard_verified_achievable`; retained task: concept 1.**

Scores refer to each concept's active generation. Solver/prediction pairs are core /
worst-family scores; counterexample scores are worst-case transition-temperature ratios.

| Concept and verification mode | Baseline | Private champion or witness | Final fresh score | Ratchets | Status | Solvability |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Anisotropic solver — A, baseline improvement | 0.400 / 0.000 | 1.000 / 1.000, twice | 0.850 / 0.500; 17/20 cases | 3 | `hard_verified_achievable` | Demonstrated under identical limits |
| 2. Matched retarded kernels — B, counterexample | 1.000000 | 1.09495584 | 1.09495944 and 1.09496470 | 1 | `solved` | Demonstrated by both fresh witnesses |
| 3. Sheet-resolved spectra — D, hidden prediction | 1.302056 / 1.708435 | 0.940259 / 1.314496, not passing | 0.921987 / 1.317465 | 0 | `rejected` | Unknown |

## Scores and fixed targets

- **Concept 1:** target core ≥0.90, worst family ≥0.75, and worst-family improvement ≥0.25 over baseline; 12 CPU seconds per case, one thread, 2 GiB. Earlier fresh generations each score 1.00 / 1.00. The preceding champion scores 0.80 / 0.50 on the final generation. The final fresh attempt uses at most 11.146 CPU seconds per case but misses three numerical gates; all three failures reproduce. The private solver passes 20/20 twice, using at most 4.119 CPU seconds per case.
- **Concept 2:** final target ≥1.09 across four spectra and all required refinements. The original-generation target is 1.12, and both original fresh witnesses score 1.12454118. Both new fresh agents independently solve the promoted minimax generation; the best score is 1.09496470.
- **Concept 3:** target core ≤1.00, worst family ≤1.25, case-p90 ≤1.75 within 180 CPU seconds. Fresh case-p90 is 1.376512 and CPU time is 68.154 seconds. Only the worst-family gate misses, by 5.4%, below the predeclared 20% substantial-failure threshold. The private portfolio also misses, with case-p90 1.437158; no passing predictor is known.
- **Fresh trials:** nine competitive, isolated `ultima-alpha` attempts, each with a one-hour limit. None times out. One administratively invalid solver launch and infrastructure smoke runs are excluded from hardness evidence.

## Counterexample and adversarial searches

- **Concept 1:** large-grid searches expose 40.50–94.79 CPU-second costs. Critical-grid searches find eight failures among twelve probes and select four branch-sensitive instances. The next champion passes all four proposed joint large/critical probes, so that axis is not promoted. Smooth, positive 96-node phonon spectra instead expose four failures under the unchanged 12-second budget: deadline-lifted controls take 44.592 and 79.780 CPU seconds, while two others stop at 90 seconds. Numerical/security checks pass 29/29; continuum checks pass 180/180. The fixture-free private solver passes 8/8 operator checks and two full same-contract runs.
- **Concept 2:** the original actual-search pool has 15 passes and eight failures over 23 completed configurations. A genuine robust-scenario gap remains at 1.08770263 versus the fixed 1.09 target and a private 1.09495584 witness. After promotion, both fresh agents solve it. The new champion's actual search passes all eight independently revalidated replay cases and reproduces its control exactly; no gap survives. A separate 24-patch probe stopped at a 600-second search-stage cap is **inconclusive**, not a one-hour hardness result.
- **Concept 3:** a private portfolio trained on 37,689 additional public-law simulations still misses the worst-family target; selection does not use hidden labels. A local ambiguity audit checks twelve cases and 105 observation-compatible pairs without severe flagged collisions, but does not prove uniqueness or attainability.

## Substantive capability and solvability

- **Retained failure:** reliable, resource-bounded convergence across large near-critical and finely resolved phonon-spectrum regimes. The final fresh solver returns valid outputs within limits, but two critical cases retain large gap/branch errors and one resolved-spectrum case remains insufficiently self-consistent. This is numerical failure, not formatting, path access, or timeout failure. The private same-contract passer demonstrates solvability.
- **Counterexample concept:** the initial method's failure under competing spectral scenarios is repaired by fresh minimax searches; the concept is solved, not retained as hard.
- **Prediction concept:** three-sheet spectral separation remains weak, but the miss is marginal. The concept is rejected rather than inflated into a hard-open claim; solvability remains unknown.

Machine-readable scores and evidence paths: `FINAL_REPORT.json`.
