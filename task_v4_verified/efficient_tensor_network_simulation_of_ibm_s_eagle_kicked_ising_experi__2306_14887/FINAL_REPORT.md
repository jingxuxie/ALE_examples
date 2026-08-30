# Hardness discovery report

Selected: **concept_2 — hard_verified_achievable**. Concept 1 is also retained as an open candidate; concept 3 is solved.

| Concept / mode | Fresh current score | Ratchets | Final status | Solvability |
|---|---:|---:|---|---|
| concept_1: Memory-bounded heavy-hex contraction planning / A | 3.66356113 | 0 | hard_open_candidate | unknown |
| concept_2: Drift-robust false finite-bond convergence / B | 95.95526637 | 1 | hard_verified_achievable | demonstrated |
| concept_3: GHZ preparation with coherent static detuning / C | 0.95241447 | 1 | solved | demonstrated |

## Baselines and champions
- Contraction: baseline core/worst 1x/1x; private 512-restart portfolio 2.166397x/1.095245x; fresh 3.663561x/1.447863x (replay core 3.663563x). Fixed targets are 4x overall and 1.1x in every family, with no greater than 5% per-case regression. The overall miss is narrow but reproducible; achievability remains unknown.
- Falsification: current weak baseline core/worst 60.163075/28.308739; preceding fresh champion 100.000000/89.490058 on the retained target (previously 100/100). The private passing witness scores 100/100, depth 24, minimum bias 0.1543807835, maximum convergence spread 0.0078956125. All 325 waveforms meet bias >=0.15 and spread <=0.008.
- Control: current weak baseline minimum fidelity 0.74826992; preceding fresh champion 0.91109149 (previously 0.96038148); best pre-attempt private candidate 0.93609347. The second fresh champion reaches 0.95241447 against the fixed 0.95 minimum-fidelity target.

## Fresh-agent scores
Five isolated ultima-alpha attempts, each with a one-hour limit, unchanged read-only participant assets, and an initially empty output directory.
| Concept | Generation | Core | Worst family / minimum fidelity | Passed | Search seconds | Timeout |
|---|---:|---:|---:|---|---:|---|
| concept_1 | 0 | 3.66356113 | 1.44786279 | False | 3205.97 | False |
| concept_2 | 0 | 100.00000000 | 100.00000000 | True | 1232.76 | False |
| concept_2 | 1 | 100.00000000 | 95.95526637 | False | 3600.46 | True |
| concept_3 | 0 | 0.96682996 | 0.96038148 | True | 1063.80 | False |
| concept_3 | 1 | 0.96840256 | 0.95241447 | True | 3152.24 | False |

## Counterexample search
- 512-restart portfolio reaches 2.166397x; fresh replay remains 3.663563x; a 36-second private variant times out on one case.
- 902 cases / 4510 waveforms: first fresh witness fails 11 of 64 knot-drift corners at +/-0.002, motivating the 325-waveform target. Private warm-start search evaluates 34 candidates / 1500 waveforms and finds a witness passing all 325 checks; a separate main-session regrade confirms it.
- 1064 independent original-model checks find no failure; static Z drift exposes a 0.911091 fidelity case at +/-0.01 rad/site/layer, motivating the 223-case target. After the second fresh agent solves it, 4929 records / 4494 unique static or matching-dependent calibrations produce no failure: minimum fidelity 0.951877878. This search is not a continuum certificate.

## Failed capabilities
- concept_1: Joint contraction-order and slicing optimization at the required hidden work efficiency.
- concept_2: Constructing a genuinely biased finite-bond convergence witness across all temporal-drift corners.
- concept_3: no remaining demonstrated capability failure; the current fresh champion passes the frozen target and all subsequent sampled stress cases.
