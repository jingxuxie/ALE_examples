# Generation-two builder report

## Scope and chronology

On August 28, 2026, main confirmed that the exact first-generation fresh v2
submission passes the unchanged original task: mean 0.050292051675201906,
worst 0.08907262925871093. It remains a valid original champion. New scaling
controls neither replace that result nor reclassify supplementary original
passes as official passes. Main owns original status and champion promotion.

The authorized resumed work began at 18:23:32 UTC. The new accuracy values were
precommitted at approximately 18:26 UTC, before any new policy trial: mean
0.075 and worst 0.125, retaining 40,000 shots, 64 queries, 4,000 shots/query,
60 CPU seconds, 3 GiB address space, 900-second episode watchdog and 300-second
startup allowance. `target_precommit.json` records the prior rationale: about
19% improvement beyond the older measured uniform local-composite control,
without copying the small-graph 0.055/0.095 thresholds.

The independent private fixtures were sampled once and frozen at
2026-08-28T18:27:53.350928+00:00. No cases were filtered for scores and no targets
or fixture parameters were changed after trials. Private and public suites use
independent randomly selected generation seeds; the earlier development suite
also has a separate seed. There have been no fresh generation-two launches.

## Actual champion's root failure

The unchanged source SHA256 is
`4f85fb71e43f6aa8a9d5d89b6462a75425a34992f2f4b6de5fac4afd5f9f0d16`.
It is byte-identical to `participant/baseline/previous_champion.py`.
The sidecar control report is at
`../../adversary/scaling_stress/runs/champion_v2_control_report.json`, relative
to this generation root. Each case used a separate byte-identical runtime copy,
the original API inside a lossless bridge, and mandatory bwrap isolation.

| Connected ladder control | Result | Worker CPU seconds |
| --- | --- | --- |
| Original D6 sanity case | Valid | 3.036710 |
| D14, 43 channels | CPU invalid | 60.238738 |
| D16, 49 channels | Memory invalid | 2.171705 |
| D18, 55 channels | Memory invalid | 5.314282 |
| D20, 62 channels | Memory invalid | 22.601420 |

At D18 the program requests a 6.23 GiB `(29,2,55,262144)` derivative temporary;
at D16 a 1.39 GiB temporary plus its resident arrays breaches the 3 GiB limit.
The model really grows as detector count increases; there is no inactive
padding. This is a measured global-outcome representation/derivative bottleneck,
not a protocol failure or a claim that calibration necessarily has exponential
complexity. Sparse parent observations avoid an artificial exponential JSON tax.
The diagnosis and algorithmic suggestions are private, not in participant TASK.

## Scientific validity

The frozen suite contains all three connected topologies at D14, D16, D18, D20.
Channel counts span 43–77 and grow with actual local edges/plaquettes. Every
detector has at least three channel incidences. The minimum expected click count
under uniform 40,000-shot allocation is 1,194.4488; all supports have graph
diameter at most two and at most four detectors. The exact law retains
overlapping hyperedges, alternate footprints, intervention-resolved aliases,
rare-channel gain ladders, and a shared hidden hot/cold shot mode.

All 12 cases pass independent local XOR-convolution PMF checks, analytic-gradient
finite differences (maximum discrepancy 8.77e-11), and direct/Poisson-parity
sampler moment tests (maximum standardized discrepancy 3.94658). The new
evaluator sampler exactly agrees with the independently validated implementation
on a shared deterministic check tape. See `validation/science.json`.

All selected-parity Jacobians and covariance-aware moment information matrices
have full column rank. Reference-only information loses four or five directions,
which interventions recover. Minimum information eigenvalue is 5.75484; maximum
condition number 141.673. Feature covariance includes cross-patch/shared-mode
terms; its smallest eigenvalue is 0.000345337, above the 1e-10 numerical floor.
Noiseless fits from two independent non-oracle initializations per fixture
recover rates within maximum absolute log error 0.000587132.

These establish local statistical identifiability, not a theorem of global
uniqueness. The moment information is not a full-state Fisher calculation or a
finite-sample qualification. Full-rank observable moments do imply local rank
of the complete observation law. Actual budgeted latent-blind trials, rather
than true-rate initialization, provide the separate achievability evidence.

## Fixed-target policy controls

All rows below run through the same isolated evaluator, with positive-rate
inference only from the public spec and queried syndromes. Private rates,
sampling seeds, scoring results, and sibling logs are outside worker mounts.
The parent never imports a submission. All 12 episodes use 40,000 shots and
respect the 64-query cap. Reports and transcripts are outside runtime leaves.

| Policy | Mean log RMSE | Worst cell | Max CPU seconds | Fixed targets |
| --- | --- | --- | --- | --- |
| Supplied weak pairwise-moment baseline | 0.105737967 | 0.166973423 | 1.378560 | Fail |
| Uniform local-composite control | 0.089878379 | 0.133301462 | 1.496039 | Fail |
| Prior-only static nonuniform design, then local fit | 0.068336339 | 0.097436169 | 1.700513 | Pass |
| Three-stage adaptive local-composite design | 0.063895114 | 0.089218468 | 4.523668 | Pass |
| Pre-existing worst-family-weighted adaptive variant | 0.063410723 | 0.088417171 | 5.200961 | Pass |

The adaptive mean is about 28.9% lower than uniform on these fixtures. A separate
six-case development suite also improves under adaptive allocation. Crucially,
the optimized static policy passes too: this demonstrates efficient inference
plus purposeful experimental allocation, NOT that observation-dependent
adaptation is mathematically necessary. No syntactic adaptivity requirement or
hidden reward bonus is imposed. A stricter claim would be unsupported.

The private local-composite estimator keeps the shared-mode mixture within
each patch but combines overlapping patch log likelihoods. Its approximate
design curvature is not falsely labeled the full likelihood Fisher. The
scientific information validation separately uses exact cross-feature
covariances. The private policy is not supplied as the starter; the actual
historical champion and a weak scalable baseline are supplied instead.

## Supplementary noise tapes and limitations

Two preselected independently seeded noise tapes retain exactly the frozen
hidden parameters and use independent runtime copies, the same API/budget/CPU,
and the same adaptive source. They are NOT replacements for the frozen score:

| Adaptive tape | Mean | Worst | Fixed thresholds |
| --- | --- | --- | --- |
| 1 | 0.066490737 | 0.103324292 | Pass |
| 2 | 0.063988549 | 0.125604883 | Fail worst by 0.000604883 |

The second tape's limiting cell is burst_aliases/boundary, not an unseen rare
channel. Thus this evidence does not guarantee uniform success over all noise
tapes, and the worst-family guard has finite-sample variability. Neither the
targets nor the frozen tape was changed in response. Any additional robust
portfolio reports are supplementary and must retain their individual outcomes.

The pre-existing `--policy robust` variant also passes tape 2 at mean
0.06241683033874857, worst 0.0960932246623387, maximum CPU 4.962595 seconds.
Its frozen-suite qualification is the additional row in the table. This does
not replace the ordinary adaptive tape-2 failure. No policy code, target, or
fixture was changed to obtain this result; both policy modes were implemented
before the first new trial. No further portfolio search is performed.

## Isolation and public-runner audit

`validation/runtime_audit.json` confirms an actual two-second process-time burn
measures 2.305446 worker CPU seconds, and a one-second CPU limit terminates the
same program at 1.023055 seconds. A 4 GiB allocation is rejected under the 3 GiB
cap. The worker cannot see host ALE paths or evaluator/private files; participant
is read-only and only its own submission leaf is writable. Parent directory
mount requests are rejected, while `attempts/audit_leaf` is accepted. The
original signed supervisor is unchanged; bwrap-monitor CPU is not used.

The public tester succeeds inside a participant-only bwrap allowlist exposing
the participant and attempt at their actual absolute launcher-style paths,
with no `/participant` or `/submission` aliases. It itself launches only an
ordinary subprocess. The copied weak baseline imports through
`DETECTOR_INPUT_DIR`; reports are written to the writable attempt directory.
See `validation/public_allowlist_command.json` and `validation/public_allowlist.log`.
The final post-edit rerun also succeeds; see `validation/public_allowlist_final.log`.

The public targets file omits only the privileged builder rationale; all its
normative values equal the unchanged frozen private targets. The private
precommit and rationale remain available for main's audit, not fresh guidance.

Original participant/evaluator hashes continue to match the original sidecar
snapshot. The original root status is not edited. Generation-two readiness and
package hashes are separate; main audits and launches any fresh participant.
