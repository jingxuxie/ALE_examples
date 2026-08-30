# Generation 2 private positive control

The revised 7.0% overall / 5.7% worst-family targets are achievable on all eight
frozen hidden cases under the unchanged 90-second, four-core, 2-GiB replay limits.
The passing implementation is `../fringe_submission/solve.py` together with
`../fringe_submission/relaxation.py`. It recomputes the LP from the received case;
no stored hidden marginals, solutions, or fresh-attempt artifacts are mounted or
read by that implementation.

## Measured result

| Family | Mean relative gain |
| --- | ---: |
| Gap hotspots | 8.423352879% |
| Inversion proximity | 7.584234448% |
| Anisotropic warping | 5.910222022% |
| Scenario competition | 6.176725184% |

`core_score = 0.07023633633344793`,
`worst_family_score = 0.059102220224818425`,
`minimum_case_gain = 0.010183163837937714`, and `resource_score = 1.0`.
All cases were feasible and strictly improved the baseline. Total measured
replay wall time was 146.035805554 seconds; per-case time ranged from
13.422954587 to 30.188883796 seconds, including process startup and LP work.
CPU affinity was four allowed cores, 380–383, separate from the slower private
prototype's cores 0–3. The per-case CPU count and all declared limits were unchanged.

The mean-gain margin above acceptance is only 0.023633633 percentage points.
This establishes a positive control for these cases, not broad robustness or
frontier hardness. Full report, case metrics, source hashes, input hashes,
read-only source snapshot, and output artifacts are in `comparison.json` and
the evidence directory named there.

## Method and simpler controls

The method solves one topology/budget/scenario LP, enumerates its small marginal
supports, allows one arbitrary vertex choice outside that support, and applies
feasible best-improvement single-site descent. This is a modest LP rounding and
repair method, not a long stochastic search or an exact global optimizer.

Plain per-vertex LP argmax rounding does not pass: two cases violate feasibility.
Cached support enumeration alone, even with single-site polishing, also missed
the revised targets. Adding the one-vertex support expansion produced the
passing candidate, which was then verified with fresh LP computation inside
each isolated replay. The original 65-second stochastic prototype incurred one
90-second replay timeout and is not a passing control; its full failed record
is preserved in `../generation2/comparison.json`.

## Manifest limitation

The root CLI refused to start because its frozen manifest still disagreed with
the recalibrated `participant/TASK.md`. No root file was edited to bypass that
check. The private controller called the exact unmodified `isolation.replay`,
`validate_result`, and `aggregate` functions, with identical limits and current
generation-2 policy. It verified that all numerical inputs and scoring/isolation
sources were unchanged throughout. The root manifest mismatch remained at finish.

After the main controller reseals its generation-2 manifest, it can independently
obtain the root CLI report from the concept directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B evaluator/evaluate.py \
  --submission adversary/headroom/fringe_submission --split hidden \
  --output adversary/headroom/generation2_fringe/official_replay.json
```

No fresh Codex sessions were launched, no stopped or running fresh outputs were
inspected, and every sidecar write remained under `adversary/headroom/`. Total
numerical work for both private replays and the short cached diagnostics was
about 788 seconds, below fifteen minutes. No further task construction follows.
