# Hardness-discovery final report

## Concepts and verification modes built

Exactly three concepts were built after screening nine candidates. All use
explicit paired-electron effective Hamiltonians seeded by arXiv:1807.01328,
not literal molecular or unrestricted FCI benchmarks.

| Concept | Primary verification mode | Final generation | Final status |
| --- | --- | ---: | --- |
| Adaptive CAS tail estimation | E — active experiment design | 2 | hard_verified_achievable |
| Persistent premature-screening witness | B — counterexample/falsification | 3 | hard_open_candidate |
| Held-out correlation-tail prediction | D — hidden prediction | 1 | solved; not retained |

## Baseline, champion, and fresh-agent scores

### Active experiment design — final target

Targets: overall RMSE10 microEh, every-stratum RMSE25 microEh, query 160 per
system, aggregate CPU 120 seconds, wall 600 seconds, memory 2 GiB. All entries
below are valid runs and use at most160 query units; query resource score 0.5.

| Artifact | Overall RMSE, microEh | Worst RMSE, microEh | Core score | Worst score | CPU seconds | Passed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Weak baseline | 58.0536 | 116.7488 | 0.419464 | 0.533005 | 0.236 | No |
| Previous fresh champion | 49.4178 | 113.0614 | 0.505822 | 0.547754 | 104.074 | No |
| Fresh generation 2 attempt | 18.1089 | 31.7704 | 0.818911 | 0.872918 | 104.060 | No |
| Privileged policy, main verification | 7.8011 | 14.8330 | 0.921989 | 0.940668 | 61.400 | Yes |

An independent fresh-policy replay again fails at 18.1165/31.7704 microEh,
CPU 104.184 seconds. Both fresh evaluations have valid protocol/resources;
construction timeout is not used as the hardness argument. The private policy
also passes an untuned 120-case holdout at 6.2062/11.3977 microEh. Its code is
observation-driven, with no hidden-label, private-coefficient, or case-ID lookup.

First-generation baseline/fresh scores were50.9183/107.0189 and
5.5792/10.3069 microEh respectively; the fresh agent solved that generation.

Evidence: `concept_1/attempts/v_2.score.json`,
`concept_1/attempts/v_2.replay_score.json`, and
`concept_1/adversary/ratchet_1/adversary/portfolio/MAIN_REVIEW.md`.

### Counterexample — final target

The nominal point conditions and radius 0.001 Eh remain unchanged. Acceptance
requires nominal success and at least 122/128 successes in each of the VV-only
and full100-coefficient perturbation families. Every row is a valid input and
all reported runs satisfy validator resources; resource score 1. A valid input
is not necessarily an accepted persistent witness.

| Artifact | VV successes | Full successes | Core score | Worst-family score | Passed |
| --- | ---: | ---: | ---: | ---: | --- |
| Zero baseline | 0/128 | 0/128 | 0.00001043 | 0 | No |
| Previous B2 champion | 128/128 | 0/128 | 0.666667 | 0 | No |
| Fresh v3 | 128/128 | 7/128 | 0.685855 | 0.057566 | No |
| Independent fresh v4 | 128/128 | 9/128 | 0.691338 | 0.074013 | No |

Both fresh artifacts satisfy nominal witness conditions. All 256 perturbed
physical-regime checks per artifact pass; full-family failures are violations
of the small-parent/large-ratio requirements. Construction times are 3349.31
and 3163.86 seconds. Official validator times are 7.10 and 5.41 seconds. The
canonical evaluator reproduces v4's score exactly.

Generation 1 was solved: fresh omitted tail63.3326 microEh, maximum triple
0.350726 microEh, ratio180.576, core 1. Generation 2 was also solved: the fresh
witness passes 128/128 perturbed cases, core 1. The previous champion on that
second-generation assay passes only10/128, core 0.541118; its zero baseline
scores 0.00001564. Those earlier passers do not establish generation 3 feasibility.

Evidence: `concept_2/attempts/v_3.score.json`,
`concept_2/attempts/v_4.score.json`, and `concept_2/status.json`.

### Hidden prediction

The frozen baseline has RMSE671.0885 microEh overall and 1426.0650 microEh worst
family. The fresh predictor achieves5.15018e-15 Eh overall and 9.37314e-15 Eh
worst family, passing the30/60 microEh targets. Static evaluation takes0.0284
seconds; offline solver CPU/RAM is not claimed to be measured. The concept is
solved and excluded from hardness retention because it admits scalar inversion.

## Counterexample and challenge searches

- Active design:600 independent same-sampler cases yield diagnostic RMSE
  7.5768/12.1503 microEh. Four of five 120-case batches meet accuracy; one scores
  10.8457 microEh overall. Nine individual errors exceed25 microEh. Two original
  wall-only timeouts are preserved but excluded from scientific hardness;
  sequential replays finish within the original wall limit.
- Two conditioned120-case batches expose a much stronger signed-cancellation
  failure. Their100 ordinary cases are shared, not 240 independent systems.
  The first gives the unchanged champion108.362 microEh worst-family error;
  the diversified, permuted final suite gives 113.061 microEh. Independent
  Hamiltonian/residual checks verify the declared weak-reference regime.
- Counterexample:6,656 scored perturbations test the actual B2 champion across
  control families/radii. Grid rows are paired, not 6,656 independent draws.
  Separate512-row confirmation at the unchanged 0.001 Eh radius gives 512/512
  VV-only successes versus 1/512 full-coefficient successes, motivating the
  qualitative final ratchet. A bounded six-run,280-evaluation private B3
  portfolio finds no passer; its chosen warm start remains128/128 VV,0/128 full.
- Prediction:the actual unchanged fresh predictor passes 194 private challenges,
  including rare ambiguous pair inversions. RMSE is 2.85047e-15 Eh and maximum
  error1.62093e-14 Eh. No meaningful hard failure survives that search.

## Ratchet generations

| Concept | Task generations built | Ratchets after initial task | Fresh attempts total | Fresh attempts on final target |
| --- | ---: | ---: | ---: | ---: |
| Active design | 2 | 1 | 2 | 1 |
| Counterexample | 3 | 2 | 4 | 2 |
| Prediction | 1 | 0 | 1 | 1 |

All seven attempts use isolated `ultima-alpha` sessions with separate empty
outputs and a 3,600-second construction limit. Counterexample v4 repeats
**generation 3**; it is not a fourth generation. No concept exceeds the cap.
An initial stdin-only infrastructure startup failure is excluded, not scored.

## Final status and solvability

- **Primary retained task: concept_1, hard_verified_achievable.** Fresh accuracy
  fails substantially; a legitimate private policy independently passes the
  identical frozen target. Solvability is demonstrated.
- **Additional retained task: concept_2, hard_open_candidate.** Both independent
  fresh attempts fail the final witness condition, and no passing solution is
  known. Solvability remains unknown; no impossibility claim is made.
- **concept_3: solved, not retained.** Solvability is demonstrated, but the
  scalar-inversion shortcut makes it unsuitable as the hard task.

## Substantive capabilities on which agents failed

- Active design: accurate adaptive CAS-tail estimation under signed cancellation
  and heterogeneous correlations within a fixed experiment/CPU budget. Its
  worst fresh stratum is mixed, not a protocol or resource failure.
- Counterexample: jointly preserving low-order cancellation, a material omitted
  tail, and weak correlation under 100-dimensional Hamiltonian uncertainty.
- Prediction: no substantive failure; inverse reconstruction solves the task.
