# Hardness discovery: mirror randomized benchmarking

## Concepts and verification modes built

| Concept | Verification mode | Participant task |
|---|---|---|
| `concept_1` | B — Counterexample or falsification | Construct calibrated Markovian Pauli noise that produces a near-exponential mirror decay with a sufficiently biased fitted infidelity. |
| `concept_2` | E — Active experiment design | Choose shot-limited mirror experiments and predict infidelities of withheld, denser gate matchings in the presence of crosstalk and SPAM. |
| `concept_3` | C — Witness or design construction | Construct native-geometry Clifford blocks with bidirectional low-weight Pauli spreading, including under every set of up to three CNOT omissions. |

## Baseline, champion, and fresh-agent scores

Scores are not comparable across concepts. Concept 1 passes at core score 100 with all witness constraints satisfied. Concept 2 requires mean family score at least 0.50, worst family score at least 0.3902439024390244, and all episodes valid. Concept 3 requires core and worst-family score 1, meaning every construction constraint passes. Concept 2 scores below are **mean / worst family**; concept 3's core and worst-family scores coincide.

| Concept | Task generation | Baseline score | Fresh-agent score | Outcome |
|---|---:|---:|---:|---|
| 1 | 1 | 84.07034 | 100.50383 | Passing champion |
| 1 | 2 | 85.82913 | 100.12813 | Passing champion |
| 1 | 3 | 87.29005 | 100.72208 | Passing champion |
| 2 | 1: 240,000 shots | 0.15904 / 0.14160 | 0.98377 / 0.98156 | Passing champion |
| 2 | 2: 12,000 shots | 0.15065 / 0.11934 | 0.89681 / 0.88157 | Passing champion |
| 2 | 3: 2,000 shots | 0.13311 / 0.10894 | 0.45153 / 0.42114 | Mean target fails; worst-family floor passes |
| 3 | 1: ideal only | 0.14286 | 1.00000 | Passing champion |
| 3 | 2: up to two omissions | 0.14286 | 1.00000 | Passing champion |
| 3 | 3: up to three omissions | 0.14286 | 0.33333; independent repeat 0.33333 | Neither submission satisfies the witness condition |

All 10 attempts used isolated, fresh `ultima-alpha` sessions through the supplied allowlisted runner, with a 3,600-second limit and initially empty output directories. Participant files remained unchanged during every attempt, and every final output matches its deadline fingerprint. The final concept-2 attempt and both final concept-3 attempts exhausted their time budgets; their saved submissions were nevertheless evaluated. `authoring/tournament_audit.json` records all 10 completed attempts with no audit problems.

The final concept-2 submission completes all 12 episodes within 2,000 shots each, with maximum measured aggregate CPU 34.682 seconds and maximum episode wall time 69.994 seconds. Its normalized runtime/resource score is 0.5. Both final concept-3 submissions are well-formed, meet the native budgets and all ideal spreading targets, but achieve faulted minimum weight 1 instead of the required 3 in every hardware family. Syntactic admissibility is not a valid construction witness.

## Counterexample search results

- **Concept 1:** Private search exposed family compensation hidden by global calibration: the first champion's separate inverse-pair overlaps were 25,466 and 3,587 instead of 28,800 and 1,920, while their weighted mixture still matched. After separate overlap constraints were added, the second champion still shifted family-conditional mean channels by up to 26 and 13 integer counts. Fresh agents solved both strengthened tasks. The final fresh witness has relative infidelity bias 0.02366969, fit residual 0.00374281, and depth-256 polarization 0.00651112. A private final-generation witness also passes, at core score 100.68503.
- **Concept 2:** Broad private shot-budget sweeps exposed prediction failures rather than mere overspending. A budget-adapted first champion failed at 12,000 shots; the next fresh champion passed. At 2,000 shots, the adapted second champion scored 0.36990 / 0.28239 on an independent confirmation set. A stronger private portfolio scored 0.41069 / 0.33151 on the final official benchmark; neither passes. The final fresh submission is better, but its mean remains 9.69% below the fixed target. The pooled 25-qubit diagnostic score is 0.31310; that diagnostic is not an additional pass condition.
- **Concept 3:** Exhaustive omission sweeps broke the first champion under one/two omissions. The second champion withstands every set of up to two omissions but fails 966 triple-omission scenarios across the three hardware families (321 / 282 / 363), scoring 0.33333 under the final target. Privileged multi-worker search found no passing construction. The two final fresh submissions fail 64,466 and 4,498 triple-omission scenarios respectively, and also fail some smaller omission sets. A post-tournament audit screened 172 unique family circuits, including 158 from 549 deadline files, without finding even one passing final-generation family or a passing portfolio. Independent scalar propagation reproduced six concrete final-submission failures.

The construction checker exhaustively enumerates the specified Pauli inputs and omission sets, rather than sampling them; its full-cap reference evaluation checks 305,832 directional scenarios and 890,561,868 Pauli images. Native propagation tests, dense small-circuit checks, malformed-artifact checks, and independent failure reproduction support evaluator validity. For concept 2, a runtime-library mount defect and a descendant-CPU accounting defect were repaired and explicitly excluded from hardness evidence. The final baseline, private portfolio, and fresh submission were scored with parent-controlled kernel cgroup CPU accounting; 56 self-checks and nine resource checks pass. Physics, hidden seeds, shot budgets, quality thresholds, and the final submitted policy were unchanged. Historical launcher CPU figures are not aggregate CPU measurements.

## Ratchet generations

Each concept underwent **two champion–challenger ratchets**, producing **three task generations**. All three initial tasks were solved. Concept 1 produced three passing champions; concepts 2 and 3 produced two each. The final concept-3 generation received two independent fresh attempts. No fourth task generation was built.

## Final status and solvability

| Concept | Final status | Solvability at final target | Retained? |
|---|---|---|---|
| 1 | `solved` | Demonstrated by fresh and private witnesses | No |
| 2 | `hard_open_candidate` | Unknown; no passing 2,000-shot policy is known | Secondary; weaker empirical hardness evidence |
| 3 | `hard_open_candidate` | Unknown; no passing three-omission construction is known | **Primary selected task** |

Earlier passing champions do not demonstrate solvability of the final ratcheted targets. Neither retained task is labeled `hard_verified_achievable`.

## Substantive capability on which agents failed

- **Primary, concept 3:** Worst-case native circuit synthesis that simultaneously preserves bidirectional Pauli spreading, connectivity, shallow depth, and gate-count limits despite adversarial CNOT omissions. Two independent agents attained the nominal objectives but not the exact fault-robust witness condition.
- **Secondary, concept 2:** Sample-efficient identification of crosstalk and nuisance SPAM from restricted experiments, followed by prediction on denser matchings, particularly at 25 qubits. One final agent missed the fixed mean target, not the worst-noise-family floor or resource limits.
- **Concept 1:** No persistent empirical capability failure; fresh agents solved both calibration-strengthening ratchets.
