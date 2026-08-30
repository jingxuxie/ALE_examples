# Larger-graph private preparation and authorized champion audit

The initial bounded preparation started August 28, 2026, at 19:14:33 UTC.
Model, portfolio, information, and integer-width preparation completed by
19:24:17 UTC. Main subsequently authorized auditing the officially passed v2
source and a conditional final-generation draft. Selection remains provisional
until main resolves v1. No fresh agent, new freeze, or root-status change occurs.

## Connected active models

Nine independently instantiated cases cover ladder, patch, triangular graphs at
D28, D36, D44. Channel counts grow from 88–110 to 140–179. Every detector is
active; degree stays at most six, support diameter at most two, and channel
support at most four detectors. The same positive-rate law, shared shot mode,
alternate footprints, aliases, and gain ladders remain. Budgets stay 40,000 shots,
64 queries, 4,000/query, 60 CPU seconds, 3 GiB, and 900 seconds wall plus startup.
All nine structural/moment/independent-sampler checks pass in `geometry.json`.

Selected local moment Jacobians are full rank. `information.json` compares
exact covariance-aware empirical-moment information at D28 and D44, including
cross-feature/shared-mode correlations. Uniform local moment asymptotic mean
log standard deviations range from .0864–.1090 at D28 to .1057–.1329 at D44.
Equal-count randomly chosen global parity MEANS have 2.54–3.25 times larger
uncertainty at D28, and 5.15–5.44 times larger uncertainty at D44.

This is only a statistic-set diagnostic. An invertible collection of parity
bits per shot can retain the entire syndrome; exact likelihood does not lose
information merely because it is represented densely. No inference about a
participant method was made from this hypothesis. The later source audit in
fact found local-neighborhood inference, not this global-mean sketch method.
These asymptotic calculations are neither a full-likelihood Fisher calculation
nor a passing latent-blind solution or impossibility proof.

## Budgeted private controls

The known private local-composite policy is copied into this sidecar only.
To avoid a separate action-count bookkeeping failure, its pilot covers 13 broad
actions and two gain levels per rare channel rather than all growing actions.
The uniform control genuinely queries every action uniformly. Both retain
unchanged inference law and the same CPU/query budget. They do not import
hidden rates or seeds, and run under the mandatory signed bwrap supervisor.

| Nine-case control | Mean regime/family log RMSE | Worst cell | Max CPU seconds |
| --- | --- | --- | --- |
| Uniform local composite | .1056135343 | .1379567422 | 7.685977 |
| Budget-aware adaptive local composite | .0791966021 | .1187903502 | 20.404400 |

All eighteen runs are valid and use exactly 40,000 shots. The new controls
demonstrate viable efficient inference and purposeful allocation, but do NOT
demonstrate the old .075 mean threshold. No new target is frozen. A conservative
accuracy proposal would need separate qualification, rather than copying the
old threshold or asserting statistical impossibility. Each size/topology has
one parameter/noise fixture, so these exploratory numbers are not robustness
guarantees or an official new-generation score.

## Actual passed source: authorized audit

After main confirmed the official v2 pass, the complete 106-file champion was
snapshotted in `actual_champion_snapshot/`; `actual_champion_manifest.json`
records every file hash. The solution SHA256 is
`e33b0f6e0f8fea0912bd186afa197e633208060be470f1191dd13f15ffeed3dc`.
Each actual-source stress uses its own complete byte-identical runtime copy.
The source reads only its isolated spec/syndromes; the parent never imports it.

The actual program uses nine-detector neighborhood likelihoods and simulated
composite-score covariance for design, followed by an unconditional full-D
likelihood refit. Its raw-mask, simulation-syndrome, and observation arrays use
int32. Those width assumptions are a distinct defect above 31 detectors; they
must not be confused with the resource mechanism established below the boundary.

All three topologies at D24 and D28 memory-fail unchanged. At D24, the terminal
`Model(spec, size=spec['detector_count'])` allocates a `(37,1,16777216)` float64
count table of 4.625 GiB, exceeding the 3 GiB cap. This happens after valid
experimentation, below the signed-32-bit boundary. D28 similarly requires 82 GiB
for `(41,1,268435456)`. Thus the failure cannot be explained solely by integer
width. Larger controls also fail; the D44 patch exits near the CPU cap, while
other D36/D44 controls report full-state allocation failures. The report keeps
the generic nonzero-exit classification where a signal was not preserved.

All results preserve the complete original source; see
`runs/actual_champion_{ladder,patch,triangular}.json`. A separate explicitly
modified diagnostic changes only raw mask/syndrome storage to int64 and replaces
the terminal global refit with the last local gradient. Its results are an
ablation, never the original champion's score. This probes whether any resource
or recovery problem remains after the obvious compatibility fixes, before
claiming a substantive final ratchet. See `runs/diagnostic_repair.json`.

## Width and protocol guard

`width_audit.json` passes all twelve combinations D24/D28/D36/D44 and topology.
A separate Python-integer XOR implementation exactly matches the int64 event
sampler on the same random tape. Sparse JSON round trips preserve every code;
large cases actually contain codes above 2**32, all remain below 2**53, and
every detector has observed clicks. The simulator/protocol is not truncating
high bits. These checks do not repair or excuse the champion's int32 casts.

Frozen original and generation-two participant/evaluator hashes are checked
throughout. All preparation writes stay in this sidecar. No pending fresh
submission was inspected before official pass authorization. Main alone owns
best-champion selection, original statuses, and any future launch/freezing.
