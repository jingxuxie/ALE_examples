# Hardness-discovery report

## Concepts and verification modes built

| Concept | Participant task | Primary mode |
|---|---|---|
| 1 | Calibration-weighted, architecture-native routing of opaque two-qubit programs | A — baseline improvement |
| 2 | Construct a regular circuit and cheaper legal route that falsify a specified routing portfolio's resource target | B — counterexample |
| 3 | Construct native CNOT circuits implementing exact binary linear maps while visiting required parities within count and depth budgets | C — witness construction |

Three concepts were built from the eight-concept shortlist in `authoring/concepts.md`. The retained participant task is `concept_3/participant/TASK.md`.

## Baseline and champion scores

Routing scores are geometric-mean cost reductions; counterexample scores are normalized constraint satisfaction; construction core scores are case pass fractions. Scores are not comparable across modes.

| Concept/version | Weak baseline: core / worst | Champion or private result |
|---|---:|---|
| Routing G1 | 0% / 0% | Fresh champion: 25.9432% / 20.9518%; 166.32 s graded runtime |
| Routing G2 | 0% / 0% | G1 champion on the new suite: 1.5215% / 0.5044%; fresh G2 champion: 67.9694% / 57.1949%, 124.60 s |
| Counterexample G1, G2, G3 | 0.055556 / 0.055556 in each version | Fresh champions: 1 / 1 in every version |
| Construction G1 | 0/6 cases / 0; resource score 0.036434 | Private exact witnesses: 6/6 cases / 1; resource score 1 |

Routing targets were fixed before launch: G1 required 15% overall and 8% worst-family improvement; G2 required 40% and 30%. The unchanged G1 submission also received a canonical recheck: 25.5686% / 20.4434% quality, but a timing outlier failed its tighter resource limit. Both records are preserved. Timing jitter is not used as hardness evidence. G2's 12-second case and 360-second summed submission-runtime limits were declared before its launch.

For counterexamples, every relabeling must simultaneously exhibit a 2.5× SWAP ratio, 16 additional SWAPs, and a 1.35× native two-qubit ratio. G3 also has a private passing witness: 113 demands, 8 certified SWAPs, and a portfolio minimum of 28 SWAPs in every family; its core/worst scores are 1/1.

## Fresh-agent scores

Every scientific trial used a fresh, allowlisted `ultima-alpha` session with a 3,600-second authoring limit and read-only participant assets. Invocation records, immutable submissions, and scores are under each concept's `attempts/`. Resource scores are mode-specific.

| Trial | Core | Worst family | Resource | Semantic/route validity | Passed | Authoring seconds |
|---|---:|---:|---:|---|---|---:|
| Routing G1 | 0.259432 | 0.209518 | 1 | valid | yes | 2823.84 |
| Routing G2 | 0.679694 | 0.571949 | 1 | valid | yes | 2643.67 |
| Counterexample G1 | 1 | 1 | 1 | valid | yes | 819.91 |
| Counterexample G2 | 1 | 1 | 1 | valid | yes | 965.21 |
| Counterexample G3 | 1 | 1 | 1 | valid | yes | 1870.28 |
| Construction, trial 1 | 0.500000 (3/6) | 0 | 0.927521 | valid | no | 3600.85 |
| Construction, trial 2 | 0.666667 (4/6) | 0 | 0.924384 | valid | no | 3530.65 |

The first construction trial reaches the deadline; the additional 0.85 seconds are termination overhead. The second trial is an independent replication of the identical frozen task, not a ratchet. Both satisfy every semantic and CNOT-count constraint. Neither satisfies the complete depth-bounded witness condition. Provided-runner revisions and startup-only aborted initializations are explicitly documented in `authoring/REPRODUCE.md`; they are not concealed or counted as additional scientific trials.

The counterexample champions use respectively 80/64/123 demands and 8/8/15 reference SWAPs. The weakest portfolio responses among the six public relabelings are respectively 66/38/72 SWAPs. All three champions are retained in `concept_2/champions/`.

## Counterexample and adversarial-search results

- **Routing, first champion:** a 72-case ordinary sweep and 36 structured cases did not establish a substantial quality failure. Separate calibrated native-interaction probes exposed a genuine blind spot: cost 674 versus exact paid-routing certificates of 185.65 and 195.10. The resulting G2 suite uses coupled nine-wire workloads, not independent pair relocation. All 48 public/hidden private certificates validate; hidden certificate improvement is 66.9122% overall and 55.0744% worst-family. The old champion manages only 1.5215% / 0.5044% on that suite. Evidence: `concept_1/adversary/champion_fuzz_1/gap_certificate.json` and `concept_1/adversary/generation_2/`.
- **Routing, second champion:** privileged generation accepted 24 of 67 twelve-active-wire phase-competition candidates, each with an exact certificate exceeding 50% baseline improvement. The champion passes all 24, with 65.5923% overall and 53.4335% worst-family improvement, 91.40 s total and 9.61 s maximum case runtime. It beats 17 private certificates, ties 5, and exceeds the remaining two costs by at most 1.474%. No substantial new quality failure supports another generation. Evidence: `concept_1/adversary/phase_stress/champion_audit/report.json`.
- **Counterexample ratchets:** case-independent long-horizon, suffix-embedding, future-emphasis, and full-program-cut policies expand the public portfolio from 18 to 25 to 62 policies. Exact repairs reduce the first champion's G2 score to 0.208333 overall / 0.125 worst and the second champion's G3 score to 0.25 / 0.25. Both repaired task versions are nevertheless solved by fresh agents. Private G3 search checks 12 preserved candidates, finds two passes, and performs 4,836 exact policy-route replays including the finalist rerun.
- **Final counterexample champion:** all 32 additional deterministic relabelings pass the frozen 62-policy method, covering 1,984 exact route replays. Portfolio costs range from 55 to 76 SWAPs against its 15-SWAP witness. A separate general window-embedding repair with portfolio-selected prefixes finds 37 SWAPs in three public families and 39 in the others; the 37-SWAP results break the 2.5× target for that expanded method. The terminal odd cycle and costly prefix-layout phases explain the failure. This does not retroactively change G3, and no fourth generation is built. Evidence: `concept_2/adversary/ratchet_search_3/audit_summary.json`.
- **Construction evaluator adversaries:** 20 negative witness mutations, parser/resource checks, and 12 independent Boolean-matrix replays validate the checker. The checker requires no reference circuit. Private witnesses, weak baseline, and first fresh artifact reproduce their saved scores exactly in the final recheck. Evidence: `concept_3/attempts/validation_report.json`, `concept_3/attempts/negative_mutations_report.json`, and `authoring/construction_recheck.json`.

## Ratchet generations

| Concept | Task versions | Ratchet updates | Fresh trials |
|---|---:|---:|---:|
| Routing | 2 | 1 | 2 |
| Counterexample | 3 | 2 | 3 |
| Construction | 1 | 0 | 2 |

There are seven scored fresh trials in total. No concept exceeds three champion generations. The construction replication changes neither inputs nor targets.

## Final status and solvability

| Concept | Final status | Solvability |
|---|---|---|
| Routing | `solved` | Demonstrated by resource-qualified fresh implementations in both versions |
| Counterexample | `solved` | Demonstrated by fresh and private witnesses; generation cap reached |
| Construction — selected | **`hard_verified_achievable`** | Demonstrated by exact private circuits satisfying all six cases |

The selected task, baseline, evaluator, and proof-of-achievability evidence are respectively `concept_3/participant/TASK.md`, `concept_3/participant/baseline/synthesize.py`, `concept_3/evaluator/evaluate.py`, and `concept_3/attempts/planted_report.json`. Private designs and generators are excluded from every participant export. No `hard_open_candidate` classification is needed for the retained task.

## Substantive failed capability

The agents construct semantically correct, count-efficient circuits but fail to jointly optimize native parallel depth, intermediate parity exposure, and the final linear transformation on grids.

| Case | Depth budget | Fresh trial 1 | Fresh trial 2 |
|---|---:|---:|---:|
| Grid, 16 qubits | 42 | 68 | 75 |
| Grid, 20 qubits | 49 | 92 | 92 |

Both fresh agents therefore have a grid-family pass rate of zero despite passing every CNOT-count bound and every exact algebraic check. This is an optimization failure, not missing output, a parser mismatch, or a timing-only failure. The private six-case passing design establishes that the required depths are feasible.
