# Hardness-discovery report

## Concepts and verification modes

| Concept | Primary mode | Final generation | Ratchet generations |
|---|---|---:|---:|
| concept_1: Inverse Eliashberg spectral prediction | D — hidden prediction | 2 | 1 |
| concept_2: Temperature-transferable collision-event compression | A — baseline improvement | 2 | 1 |
| concept_3: Matched-observable transport falsification | B — counterexample/falsification | 1 | 0 |

## Baseline and champion scores

A/D entries are core / worst-family scores out of 100; their fixed target is 80 / 70.

| Concept and generation | Runnable weak baseline | Champion from previous generation on this generation |
|---|---:|---:|
| concept_1, generation 1 | 68.8005 / 60.3960 | — |
| concept_1, generation 2 | 59.1601 / 53.2876 | 75.5929 / 73.0059 |
| concept_2, generation 1 | 0.1713 / 0.0101 | — |
| concept_2, generation 2 | 0.3457 / 0.2822 | 0.0000 / 0.0000 |

Concept 3 baseline trace ratio: **1.023017903**, versus the fixed **1.75** witness target. No passing witness champion is known.

## Fresh-agent scores

| Concept / generation / attempt | Time (seconds) | Score | Target met |
|---|---:|---:|---|
| concept_1 / 1 / v_2 | 1968.4 | 83.5181 / 80.0027 | yes |
| concept_1 / 2 / v_3 | 3497.1 | 0.0000 / 0.0000 | no |
| concept_2 / 1 / v_1 | 1720.5 | 99.9178 / 99.8990 | yes |
| concept_2 / 2 / v_2 | 1492.1 | 97.6124 / 96.5903 | yes |
| concept_3 / 1 / v_1 | 2892.6 | trace ratio 1.697351674 | no |

All scientific attempts use isolated fresh ultima-alpha sessions with a 3,600-second limit. One generation-1 spectral attempt terminated externally after 111.4 seconds and is excluded as infrastructure failure; its unchanged-task fresh retry is included.

The final spectral submission has official score 0 because CUDA-linked Torch cannot load under the 3-GiB address-space limit. This technical failure is not used alone as scientific hardness evidence. A separate, nonofficial run of the **unchanged submission**, with only the address-space ceiling raised to 16 GiB, completes in 31.2 seconds and scores **75.9348 / 73.7085**. Its mean physical loss is 23.37% above the core-target allowance, and it meets the predeclared substantial-failure margin (core at most 76). A conditional stratified-bootstrap 95% interval for core score is 75.1248–76.7166. This diagnostic is neither an official pass nor a repaired implementation. The frozen task wording did not distinguish RSS from address space; this resource ambiguity is explicitly not the sole basis for retention.

## Counterexample search results

- Spectral prediction: 6,144 private outcomes across four observation regimes identified the warm, noisy, weak-coupling failure. The original champion scored 75.6556 / 73.8040 there, and 75.5929 / 73.0059 on the new independent hidden generation. Public training and validation were regenerated in the same disclosed regime.
- Collision compression: 28 private first-champion cases yielded 26 successes and two allocation failures. Larger published catalogues exposed the same memory-representation failure. The second fresh champion passed the task and all eight subsequent private probes, including up to 896 states and weakened inter-valley channels; the lowest probe score was 95.8668.
- Matched-observable falsification: 30 privileged LP-vertex search restarts found a best admissible trace ratio of 1.653272048, not a passing witness. The fresh agent found 1.697351674; independent Fourier and shifted-grid collision solves agree to approximately 1.7e-14. No tested construction reaches 1.75.

## Final status and solvability

- concept_1: **hard_open_candidate**; solvability **unknown**. The official fresh submission fails the address-space limit. A separately isolated, unchanged-submission diagnostic scores 75.9348 core and 73.7085 worst-family, misses the fixed 80/70 target, and meets the predeclared core-score substantial-failure margin of 76. No passing generation-2 predictor is known; generation-1 success does not establish generation-2 achievability.
- concept_2: **solved**; solvability **demonstrated**. The second fresh agent exceeds both fixed targets. Eight additional private probes, including larger catalogues and weakened inter-valley channels, remain valid and above target. No scientifically justified further ratchet was identified.
- concept_3: **hard_open_candidate**; solvability **unknown**. The fresh agent produced an admissible, independently verified pair but did not reach the fixed 1.75 transport-trace ratio. The private search also found no passing witness; feasibility is not demonstrated.

Primary retained task: **concept_3**, **hard_open_candidate**. Its target feasibility remains unknown. Exact-label and over-budget identity validation scores are not evidence of participant achievability.

## Substantive capability failures

- concept_1: Recovering spectral shape from warm, noisy, weak-coupling imaginary-axis measurements remains below the fixed accuracy target despite learned ensembles and posterior refinement. The unchanged model's mean physical loss is 23.37% above the target allowance even after its library-loading restriction is relaxed.
- concept_2: The first champion exhausted memory building full-edge repeated-temperature feature matrices. The fresh generation-2 agent overcame this scalability failure; no unresolved failure was found in the final private probes.
- concept_3: Global construction of bounded smooth reciprocal scattering kernels with matched full low-order observables but sufficiently different exact transport.
