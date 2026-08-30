# Ratchet 1 investigation: no stronger generation recommended

Completed August 28, 2026. **Keep concept_3 generation 1 marked solved. Do not
launch a fresh session on the provisional case set from this investigation.**
No participant, evaluator, champion archive, or root status file was changed.
No fresh model was launched. All work products are under this directory.

## Decision and measured results

| Experiment | Joint recovery | Worst family | Target gates |
|---|---:|---:|---|
| 56 queries, 48 independent draws | 47/48 | 15/16 | met |
| 56 queries, 48 boundary draws | 44/48 | 14/16 | met |
| 56 queries, combined screen | 91/96 | 29/32 | met |
| Initially postselected balanced 12 | 8/12 | 1/4 | not met |
| **Same unchanged champion, full re-evaluation of those 12** | **12/12** | **1.0** | **met** |
| 40 queries, 24 independent controls | 24/24 | 1.0 | met |
| 32 queries, same 24 independent controls | 21/24 | 6/8 | met |
| 32 queries, five initial 56-query failures | 4/5 | not meaningful for absent families | diagnostic only |
| 32 queries, provisional balanced 12 | 11/12 | 3/4 | met |

The final 56-query re-evaluation has exact support and vortex configurations on
all twelve cases, mean relative strength error 3.75e-9, mean wall time 43.72s,
and maximum wall time 73.40s. The 32-query cross-check also meets every original
quality gate: F1 0.95238, relative strength error 0.11197, and vortex accuracy
11/12. Nothing here justifies claiming a validated hard ratchet generation.

All reports use `target_met_on_this_sample` for the original absolute gates.
Their `passed=false` field means these are nonofficial experimental suites; it
does NOT mean a failure of the reconstruction target. There are no protocol
failures in the reported screens/rechecks/frontiers.

## Search design and scope

`cases_96.json` was frozen before scoring: 16 independent public-prior draws per
family, plus four rejection-conditioned draws for each of four physical regimes
and each family. Every accepted scene is literally `draw_scene(seed,family)`
from the unchanged public model, with no manually altered latents:

- Weak adjacent opposite-sign potentials with similar magnitudes, maximal count,
  and at least one vortex.
- Two neighboring vortex cores, with at least two nearby impurities.
- Compact 4×4 support, maximal count, and several large signed strengths.
- Interior-edge-heavy support containing both weak and strong impurities.

The screening manifest records the exact predicates, private seeds, and rejection
counts. There were 14,886 prior draws including rejected candidates. All 96
scenes use 56 scalar queries, 90 CPU seconds, 120 wall seconds, one pinned CPU,
and the unchanged quality targets. Process-level workers avoid mixing independent
episodes' child accounting. Only the three byte-identical champion solver files
are mounted as submission, never the archive's private evaluator subtree.

## Why the apparent counterexamples were rejected

The initial five failures were all valid JSONL episodes with incorrect support
and/or vortex positions, not protocol errors. Four failed both first replays;
one recovered on both replays and was immediately excluded from curation.
The remaining four plus eight slow successful controls formed a frozen,
balanced twelve-case proposal. That proposal then **entirely recovered** in a
fresh full-suite re-evaluation using identical source, latents, and resource
limits. For all four disputed cases, the full 56-query transcripts are identical
between failure and success; the difference is how far nonlinear search gets
before its internal CPU guard.

For example, `independent-crowded-13` stopped after roughly 16.6k–17.8k evaluations
in failed runs but reached its exact solution after 23,974 evaluations in 72.95
observed CPU seconds in the final run. `weak_dipoles-crowded-0` likewise recovered
after 17,589 evaluations in 62.67 observed CPU seconds. The source guards at 83
CPU seconds or 110 wall seconds; core assignment/load/throughput are not fully
controlled by the helper. Some replays reached the wall guard with only 70–73
observed CPU seconds. These are real budget-sensitive search failures, but not
stable evidence for a harder physics distribution on this hardware setup.

Initial clusters were (a) signed-support local minima in strong multiple-scattering
scenes and (b) a coupled wrong-support/wrong-vortex-position minimum for a weak
opposite-sign pair scene. No matched-site sign mistakes occurred in the four
initially repeated failures. Features characterize association, not a claimed
single-variable causal ablation. Changing initial query allocation repaired
four of the five initial failures even at 32 total queries, further weakening a
claim that their difficulty comes from a fundamental observation deficit.

## Evaluator validity and resource caveat

`verify_cases.py` independently constructs hopping by Kronecker products and
pairing by complex displacement unit vectors rather than the production loops
and phase-angle formula. It checks every scene against its exact prior draw,
Hermiticity, paired particle-hole spectrum, the complete LDOS table, direct
resolvent columns, actual instrument observations, and independently calculated
support/strength/vortex metrics. The full 96-case scored screen and the selected
twelve cases pass. Instrument residuals are at rounding scale (about 5e-13).

The initial wrong estimates had queried LDOS RMS errors 0.0201–0.0416, far above
rounding. True-support Jacobians had minimum singular values 0.0947–0.1712 and
condition numbers 4.53–7.02. Thus the specific wrong scenes are distinguishable;
these finite/local checks are not a global identifiability proof or a label-oracle
solver. All scored reconstructions ran in fresh Sandbox subprocesses, with no
hidden labels in stdin or mounts.

The production `cpu_seconds` field uses `os.times()` and counts mostly bwrap
overhead on this host, not its nested solver. This was discovered and reported,
not silently repaired in production. `observed_sandbox.py` adds read-only kernel
process-tree sampling for replay/frontier runs and records CPU lower bounds and
one-core affinity checks; inherited hard limits are unchanged. Parent integration
should fix CPU reporting and control/normalize hardware throughput before relying
on rare timeout counterexamples. Wall-time measurements remain valid.

## Artifacts and handoff

- `GOAL_PACKET.json`: machine-readable decision, all score summaries, individual
  failure/recovery histories, protected hashes, and unchanged quality target.
- `screen_96/report.json`: complete initial screen and transcripts.
- `recheck_56/`, `additional_recheck_56/`: ten repeat measurements.
- `proposed_cases_12.json`: **rejected provisional** balanced adversarial set;
  preserve for reproducibility, not as an approved new hidden evaluation.
- `proposed_reevaluation_56/report.json`: decisive 12/12 recovery.
- `frontier_40/`, `frontier_32/`, `proposed_frontier_32/`: query-frontier evidence.
- `proposed_public_calibration.json`: six independent labeled physical-regime
  examples, generated without filtering on champion performance; proposed only.
- `validity_*.json`: independent numerical and scoring checks.
- `protected_hashes.json`: participant/evaluator/champion preservation audit.

183 isolated champion episodes were run. The only resource-frontier code change
was replacing the initial fixed-query slice `44` with `max(4,query_budget-12)`;
at 56 it is exactly the original policy. No hidden truth or label-assisted fit
is counted as a passing solution. Neither the 40-query nor the 32-query results
support an immediate stronger-generation launch under the original quality gates.
Further work would require a new, approved scientific regime or a controlled
compute-cost contract, not postselecting one unfavorable timing run.
