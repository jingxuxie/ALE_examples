# Hardness-discovery results

## Concepts and verification modes built

Exactly three concepts were built from ten considered candidates. The primary retained task is **concept 3**, exact topology-constrained Clifford construction.

| Concept | Verification mode | Fixed acceptance target |
| --- | --- | --- |
| 1. Robust detector-readout compression | A — baseline improvement | At least 20% mean relative risk reduction and 10% reduction in every family; all six hidden outputs valid; 45 solver seconds, one CPU, 2 GiB per instance |
| 2. Bounded distance-certificate falsification | B — counterexample | Current generation: at most 36 faults, exactly zero detector syndrome, and odd logical parity; the supplied overconfident wrapper's false claim is reproduced |
| 3. Exact Clifford construction on a grid | C — witness construction | All 72 signed generator images exact on the native 36-qubit grid; at most 336 CX, 23 entangling layers, and 1648 total gates |

## Baseline, champion, and fresh-agent scores

Every scientific attempt used a fresh isolated `ultima-alpha` session with a one-hour allowance. Seven scientific attempts completed across the tournament and ratchet. The two additional runner-hash-guard blocks made no model calls and are excluded.

| Concept / generation | Baseline or current champion | Fresh-agent result | Private passing artifact or implementation |
| --- | --- | --- | --- |
| 1 / generation 1 | 0% relative reduction | `v_1`: **-2.2132%** mean reduction; **-62.3926%** worst-family reduction; valid outputs, resource score 1, target missed | Generic safe portfolio: **34.4890%** mean reduction, **10.5883%** worst-family reduction, resource score 1; passes |
| 2 / generation 1 | Empty baseline: **0 / 1** | `v_1` and `v_2`: **1 / 1** each; valid 20-fault counterexamples; solved | Independently validated 20-fault witness: **1 / 1** |
| 2 / generation 2 | Promoted champion's frozen 56-fault exact logical word: **0.746428571429 / 1**; invalid weight | `v_5`: **0.772508445946 / 1**, 37 faults and 10 nonzero detectors. `v_6`: **0.76625 / 1**, 40 faults and 8 nonzero detectors. Both odd logical parity; neither valid | Independently validated 36-fault, zero-syndrome odd logical witness: **1 / 1** |
| 3 / generation 1 | **0.178253 / 100**; 18116 CX, 12903 entangling layers, 19039 gates | `v_1`: **34.328358 / 100**, 449 CX, 67 entangling layers, 1175 gates. `v_2`: **38.333333 / 100**, 449 CX, 60 entangling layers, 2202 gates. Both exact and native; both miss budgets | **100 / 100**; 240 CX, 16 entangling layers, 1177 gates |

Concept 1's family reductions are -62.3926% biased, 10.5883% correlated, and 45.1648% drifting for the fresh submission. The private portfolio obtains 47.7140%, 10.5883%, and 45.1648%, respectively. A negative reduction means worse risk than the baseline. The private portfolio is generation-time work, not a fresh-agent success or a champion ratchet.

Concept 2's fractional scores are diagnostic only; no fractional score constitutes a valid counterexample. Both generation-2 sessions finished normally, after 3399.61 and 3582.08 seconds. Concept 3's second session reached its one-hour deadline with a complete checkpoint artifact. The other scientific sessions finished normally.

## Counterexample search results and ratchet generations

- **Concept 1: zero ratchets, one task generation.** The fresh result missed the original target. Its catastrophic biased-family fallback was confirmed by an independent probability implementation and native Stim sampling. A generic baseline-preserving, shorter-deadline portfolio subsequently passed the unchanged target under the same resource limits. All 18 baseline, fresh, and private-portfolio scored answers also agree with independent forward categorical dynamic programming.
- **Concept 2: one ratchet, two task generations.** The solved generation-1 champion was tested on eight independent, same-size private models: two each with planted witness weights 24, 28, 32, and 36. At 60 search seconds per model, all eight champion outputs failed their witness bounds; the best exact logical words had weights 52–56. Failures form one genuine search-coverage cluster: the champion's fixed information-set search fails to expose the rarer low-weight logical dependency. The selected weight-36 case preserves the 512-fault, 192-detector dimensions and is independently validated in the native circuit. Both completely fresh challengers then failed. An audit of **101 saved candidate artifacts** found no valid witness; their best saved exact odd logical words had weights **47 and 49**.
- **Concept 3: zero ratchets, one task generation.** Neither fresh attempt met the fixed construction budgets, so no solved champion needed ratcheting. Independent signed-tableau checks, native Stim comparisons, and a semantically equivalent noncanonical private circuit all confirm that acceptance is semantic and resource-based, not an exact-file comparison.

## Final status, solvability, and failed capability

| Concept | Final status | Solvability | Substantive failed capability |
| --- | --- | --- | --- |
| 1 | `hard_verified_achievable` | Demonstrated by a resource-compliant private portfolio | Deadline-safe minimax decoder optimization and safe preservation of solution quality. The fresh search found strong solutions on most cases; the evidence is specifically a pipeline-robustness failure, not an inability to find good tap sets |
| 2 | `hard_verified_achievable` | Demonstrated by a private exact 36-fault witness, checked algebraically and in Stim | Finding an exact sparse odd logical dependency rather than an overweight exact word or a low-weight near-zero syndrome |
| 3 — **primary** | `hard_verified_achievable` | Demonstrated by a private compact native circuit | Joint topology-aware CX-count and entangling-depth optimization while preserving the complete signed Clifford action |

**Overall final status: `hard_verified_achievable`.** The primary participant task is `concept_3/participant/TASK.md`; its static evaluator is `concept_3/evaluator/evaluate.py`. Solvability is demonstrated, not unknown. The result is empirical hardness under the recorded fresh-agent budgets, not a proof that no other solver could succeed.
