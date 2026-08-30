# A2 phase-stress champion audit: passed

The exact immutable `concept_1/attempts/v_2.frozen` submission passes all 24 frozen phase-stress cases using the unchanged G2 evaluator algebra and isolated shared sandbox. Core improvement is **65.5922558735%**, and worst-family improvement is **53.4334896608%** (ring), exceeding the fixed 40% / 30% objectives. All 24 answers are exact-valid; no baseline cost regression occurs. The minimum individual improvement is 52.2043391510%, so this result does not conceal a below-40% individual case through aggregation.

## Quality against both references

The original baseline is the fixed zero-improvement reference. Private certificate values are feasible route costs, not optimal-cost claims.

| Family | A2 improvement | Private certificate improvement | A2 / certificate geometric cost |
| --- | ---: | ---: | ---: |
| Chain | 55.4229651800% | 50.6399129942% | 0.9030987894 |
| Ring | 53.4334896608% | 51.7870482036% | 0.9658506398 |
| Grid | 73.3650858039% | 72.2891502046% | 0.9611727678 |
| Ladder | 74.6359114149% | 74.6359114149% | 1.0000000000 |
| Tree | 59.7830910987% | 59.2313967263% | 0.9864676656 |
| Modular | 70.5779398706% | 70.3942958933% | 0.9937970069 |

Across the pool, the private certificates achieve 64.4490130585% core improvement, below A2's achieved core score. There is no substantial certificate gap under the prospectively recorded diagnostic definition (15% excess certificate cost and five percentage points of baseline-normalized headroom). The largest relative certificate cost excess is only 1.4737179340% on `phase_stress_modular_0`; its baseline-normalized headroom is 0.4162115699 percentage points. The largest baseline-normalized headroom is 0.5852824421 percentage points on `phase_stress_ring_0`, with 1.2397325797% relative certificate cost excess. Neither is a task-quality failure or a scientific basis for another generation.

## Resources and integrity

- Primary suite execution time: **91.3973912075 seconds**, under 360 seconds.
- Maximum case execution time: **9.6062540200 seconds**, under 12 seconds.
- All processes passed execution and validity checks. There were no failed/over-limit cases requiring timing reruns; no timing-only hardness is claimed.
- The original 1-CPU, 2-GiB, 128-MiB-submission sandbox contract is unchanged.
- Parent stress inventory, G2 evaluator/checker, shared sandbox, and every frozen submission file were hash-checked before and after execution. Audit-only artifacts remain inside this directory.
- Raw per-case outputs and legal routes are private replay artifacts. No fresh agent was launched; no generation 3 or target adjustment was made.

## Why the structured workload did not expose a new failure

Inspection was restricted to the authorized frozen A2 entry and router source. `concept_1/attempts/v_2.frozen/router.cpp:141` partitions traffic into embeddable blocks with at most four active wires. `concept_1/attempts/v_2.frozen/router.cpp:184` represents paid token movements together with calibrated block execution costs. `concept_1/attempts/v_2.frozen/router.cpp:741` searches route/order and block-boundary alternatives while scoring full emitted routes.

Consequently, A2 is not restricted to a single initial layout. The stress pool increases cumulative active wires to twelve and requires paid changes between epochs, but each epoch still has four active wires, within the solver's represented local state. This is an explanation consistent with the observed pass, not a claim of global optimality or universal robustness. No cases with larger simultaneous coupled epochs were generated or evaluated in this audit.

## Recommendation

Record **champion audit passed** and retain A2 as solved. This frozen stress pool provides no genuine new quality failure from which to justify or calibrate a final G3 target. Do not raise a target after observing these scores merely to obtain a failure. Any future ratchet would require separate prospectively specified workloads, independently valid feasibility certificates, and actual reproducible quality-failure evidence before a fresh launch.
