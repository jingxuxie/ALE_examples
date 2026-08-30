# Focused tranche: measured decision evidence

Twelve in-domain N64/d14 configurations; six odd, four even, two nonzero-field unrestricted.
Every baseline and repeated v4 output is physically valid and within its observed 40-second CPU/120-second wall limits.
These are private source-native measurements, not frozen evaluator grades.

## Confirmed same-cap gaps

| Case | Sector / cap | V4 energy | Attainable reference | Gap | Screen multiple |
|---|---|---:|---:|---:|---:|
| `f2_even_quartic_interfaces` | even / 12 | 42.75775516986940 | 42.75769752562163 | 5.764424777e-05 | 9.006914 |
| `f2_odd_edge_islands` | odd / 12 | 43.82508174483624 | 43.82505206056837 | 2.968426787e-05 | 4.638167 |
| `f2_even_dimerized` | even / 14 | 39.58808647866346 | 39.58807051335327 | 1.596531019e-05 | 2.494580 |
| `f2_odd_three_soft_regions` | odd / 12 | 43.83009834398849 | 43.83009068640774 | 7.657580753e-06 | 1.196497 |

The screen remains exactly 6.4e-6; it has not been relaxed. The three-soft-region case is only 1.20 times screen and is marginal for selection.
Every listed gap survives a fresh v4 repeat and independent corrected-teacher refinement of the v3 seed. References are attainable same-bond MPS energies, never exact energies.

## Root cause and limits

The differing virtual-charge cuts are 4/5/61 (quartic interfaces), 9 (edge islands), 3/61 (dimerized), and 3/61 (three soft regions). The initial tranche's controlled reallocation rescue proves the mechanism in the original disordered case; these follow-up charge differences are measured associations.
The even random-block control instead favors v4 despite identical charge counts, so not every v3/v4 difference is a charge-count effect.
Both field controls show no screened gap against the retained alternatives. The extra parity-projected initializer is refined with the original nonzero field and unrestricted sector; its final energy 45.458604537035605 is higher than v4's 45.45857413246858, so it is not a failure reference.

## Selection assessment

This tranche does not establish an eight-case robust hard G2 suite. Three stronger follow-ups plus the original 4.32-times-screen case could supply four in-domain allocation cases if another independently verified frontier warrants a combined suite. The fourth follow-up should not be presented as a large-margin case.
V3 already attains the lower branches in valid cold long-budget runs. Allocation-only G2 may be inexpensive to repair; neither a combined portfolio nor the full future 6/40-second target has been tested here.
An unrestricted zero-field fixed-cap parity tradeoff was identified as a future hypothesis, not run: an even exact ground state does not imply an even best capped MPS. No thirteenth configuration or out-of-domain control was launched, and main's scaling search was not inspected.

## Provenance and compute

Recorded child + coordinator + initialization + final-measurement CPU: 967.257 seconds; including a 60-second ad-hoc-analysis allowance: 1027.257 / 1200 seconds. Per-child wall/CPU, requests, NPZ states, source hashes, and negative controls are retained.
`CANDIDATE_EVIDENCE.json` contains requests, reference paths, hashes, timing records, and charge-allocation differences. `SUMMARY.json` preserves all twelve comparisons; `AUDIT.json` records domain and source checks. No public, evaluator, calibration, attempt, status, target, or generation asset was edited.
