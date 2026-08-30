# Empirical decisions

Nine seed concepts were screened in `concept_selection.md`; exactly three
concepts were built, using verification modes E, B, and D. Ratchets below are
new generations of those concepts, not additional concepts.

## First tournament

All three isolated `ultima-alpha` attempts met their frozen targets. A timeout
does not invalidate an otherwise complete saved artifact: the first active
policy was saved before its one-hour construction deadline and passes the
independent inference-time accuracy, CPU, query, and memory checks.

- E: baseline overall/worst-family RMSE 50.9183/107.0189 microEh; fresh
  5.57921/10.3069 microEh. Corrected namespace-wide CPU accounting measures
  102.787 seconds, below the unchanged 120-second limit. The accounting
  amendment changes neither participant assets, hidden cases, nor targets.
- B: the fresh point witness has a 63.3326 microEh omitted tail, a 0.350726
  microEh maximum triple, and ratio 180.576. Its first private robustness
  search reveals instability under small admissible coefficient changes.
- D: fresh RMSE is 5.15018e-15 Eh versus a 671.088 microEh baseline. Independent
  analysis identifies a scalar-inversion shortcut. The actual unchanged
  champion also passes 194 further cases, including rare ambiguous pair
  inversions. This concept is solved, not retained as hard.

## Counterexample generation 2

The target is nominal success plus at least 122 of 128 independent, fixed
box-truncated coefficient perturbations of radius 0.001 Eh. It was frozen
before a new isolated attempt. On that assay, the original fresh champion
passes 10 cases, the private original author witness 43, and the zero baseline
none. No prior submission or private feasibility witness is supplied to the
new agent.

The generation-2 fresh witness passes all 128 hidden perturbations and the
nominal conditions after 1,709.52 construction seconds. Its nominal omitted
tail is 104.9999 microEh and maximum triple 0.834271 microEh. It is archived as
the second champion. This is evidence against declaring the first robustness
ratchet hard. Broader physically meaningful perturbations are investigated
privately before any further generation is selected.

## Active-policy failure search

Six hundred independent same-sampler cases are evaluated in five 120-case
batches. Two original wall-only timeouts are preserved and replayed with
additional wall-clock headroom while retaining the original CPU, memory, and
query limits. Such infrastructure timing failures are not scientific hardness
evidence.

The completed 600-case diagnostic has RMSE 7.57679 microEh, worst-family RMSE
12.1503 microEh, nine individual errors above 25 microEh, and maximum error
100.218 microEh. Four of five batches pass the accuracy target; one has
10.8457 microEh RMSE. Both sequential timing replays finish below the original
180-second wall limit, although their original timeout reports are retained.
The conditioned failures below are substantially stronger than that marginal
same-sampler failure and motivate the selected active-policy ratchet.

A separate conditioned search embeds known cancellation cores into genuinely
active eight-virtual systems. The first batch yields an actual, resource-valid
champion failure: 47.0136 microEh overall and 108.362 microEh worst-family RMSE.
The added virtual has nonzero substantial singleton correlation; independent
Hamiltonian checks confirm the weak-reference and gap constraints. A second
batch diversifies the cores and permutes virtual orbitals to avoid a fixed-slot
or repeated-core artifact. These are explicitly conditioned stress cases, not
an IID claim about the original sampler. Any resulting task generation must
declare that broader scope before a fresh attempt.

## Frozen ratchets and independent feasibility

The diversified E2 suite is frozen before its fresh launch. Its unchanged weak
baseline scores 58.0536/116.749 microEh overall/worst; the original champion
scores 49.4178/113.061 microEh and fails. Only wall-clock headroom is relaxed
to 600 seconds to avoid host scheduling noise; CPU 120, query 160, memory 2GiB,
and accuracy10/25 microEh remain unchanged.

A 13.6-minute private portfolio subsequently finds an observation-driven E2
policy, without private coefficient or label lookup. Main independently
confirms 7.80110/14.8330 microEh overall/worst, CPU 61.3996 seconds and
wall 85.9502 seconds. A separate, untuned conditioned holdout scores
6.20621/11.3977 microEh. The neural weights remain byte-identical to the
generation-1 fresh champion. These privileged artifacts are never given to
the running fresh E2 agent. E2 solvability is demonstrated; hardness still
requires that fresh attempt's result.

The actual B2 champion is challenged on 6,656 scored perturbations. Grid rows
are paired across families/radii and must not be counted as independent draws.
A separate 512-row confirmation at the unchanged 0.001 Eh scale yields
512/512 VV-only successes but only 1/512 for full-coefficient uncertainty.
All original physical-regime and numerical checks are retained. The failure
is loss of the small-parent/large-ratio condition, not a numerical artifact or
an invented claim that the original point witness is invalid.

B3 therefore retains all nominal thresholds and the 0.001 Eh radius, but
requires 122/128 successes in each of two independent finite assays: original
VV controls and all 100 coefficients of the restricted paired model. It does
not claim robustness for unrestricted electronic integral tensors. Main
independently passes 23 evaluator tests. A prelaunch additive baseline-directory
amendment duplicates only the original zero artifact; the 20-file freeze,
readiness hash, and prior freeze are recorded before launch. The B2 champion
scores 128/128 VV and 0/128 full, while the best prior private reference scores
80/128 VV and 1/128 full. No tested reference yet demonstrates B3 feasibility.

A bounded B3-specific private portfolio subsequently completes six runs and
280 objective evaluations in 10 minutes 13 seconds, including final audit.
It finds no better robust witness than the unchanged B2 warm start: nominal
and VV pass, full uncertainty is 0/128. This finite negative search is not an
impossibility claim. All 20 frozen files remain unchanged.

Two completely independent fresh attempts are launched on this same final B3
target so that any counterexample-hardness verdict requires both to fail.
`attempts/v_3` and `attempts/v_4` both have `generation=3` in their launch
manifests. The latter is replication, not a fourth concept or fourth task
generation. Each receives only the identical read-only participant packet and
its own initially empty output directory, with a separate 3,600-second limit.

## Active-policy final result

The generation-2 fresh attempt completes its enforced one-hour window with a
runnable saved policy. Official RMSE is 18.1089 microEh overall and 31.7704
microEh in the worst (mixed) stratum, versus fixed targets 10/25. It uses
query 160, aggregate CPU 104.0597 seconds, wall 125.127 seconds, and about 59 MiB
policy RSS. Protocol and resource checks pass; accuracy fails substantially.
An independent run through the promoted canonical evaluator gives
18.1165/31.7704 microEh, again resource-valid and failing. The small timing-driven
difference cannot change the verdict. Since main independently verified the
private 7.8011/14.8330 microEh passing policy, E2 is retained as
`hard_verified_achievable` with demonstrated solvability.

## Counterexample final result

Both independent final-generation fresh attempts produce valid nominal points
and pass all 128 VV perturbations. Full-coefficient successes are only 7/128
and 9/128, versus 122 required. Every perturbed physical-regime check passes;
failure is the small-parent/large-ratio condition, not numerical instability or
an inadmissible Hamiltonian. Construction durations are 3349.31 and 3163.86
seconds. Both static validator runs satisfy resource limits. Main's canonical
replay reproduces the second score exactly, and all 23 canonical tests pass.
No known reference passes the final assay. B3 is retained as
`hard_open_candidate`; feasibility is unknown, not proved impossible.
