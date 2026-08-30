# Extra refinement and non-fresh provenance

This is a **privileged, non-fresh generation-2 achievability witness**:
`is_fresh_submission: false`. It reuses completed generation-1 v2
optimizer/control/checkpoint assets and authorized frozen generation-2 cases.
Generation-2 fresh trial outcomes are **not observed or classified here**.
No live generation-2 submissions, artifacts or logs were read. No optimization
continues. No participant, evaluator, generation, champion or attempt file changed.

## Unchanged proof control

- Raw SHA256: `14e1480d990bbd59998af6ce86d97ce791c9fc23ef73f4e391b5bc3ccfe6214c`.
- Canonical SHA256: `f37ce864fe17b04107d07931b2df71e94390fe9f3959798c422d4418300c03e8`.
- The actual official score and `evaluation.json` are unchanged:
  core `.9920604212181239`, family `.985187020602394`, minimum `.9801527768159763`.
- Only provenance labels in `proof.json` and its matching manifest were clarified.
  Their earlier exact contents are preserved as `proof.pre_clarification.json`
  and `manifest.pre_clarification.json`. No fresh-trial outcome is asserted.

## Extra 160x80, dt=.0025 confirmation

The 80x40/dt=.01 scan of all 37 cases reproduces the official global boundary
maximum **exactly**: `8.863390198214215e-9` at `ratchet_example_01`.
The worst audited-fidelity case is `focused_joint_00`.
Both receive independent 160x80 stationary references and evolution, with
boundary mass and norm checked **every timestep**, not just sparse snapshots.

| Case | Extra fidelity | Change from frozen C | Dense boundary maximum |
| --- | ---: | ---: | ---: |
| `focused_joint_00` | 0.980160816479 | 6.64658e-07 | 6.29553693498e-10 |
| `ratchet_example_01` | 0.980618468813 | 1.95185e-06 | 6.55428579553e-09 |

All supplementary checks pass. The largest dense boundary mass is
`6.55428579553e-09`, leaving
`3.44571420447e-09` below the
unchanged `1e-8` guard; both dense maxima occur at T=8.
Maximum state distance from prolonged frozen C is
`1.08844760139e-05`;
reference residual is `2.97157419227e-07`;
maximum norm error is
`2.79110068391e-13`;
maximum spectral tail is
`1.41759883357e-18`.
Boundary masks have grid-dependent quadrature sampling, so raw boundary estimates
need not converge monotonically. This confirms the two selected extremes, not a
new all-37-case score or a changed acceptance criterion.

## Compute accounting

- Three bounded optimizer runs: 146 + 61 + 38 = **245 iterations**,
  **265 objective evaluations**, each over 37 cases (9,805 case objectives).
- Optimization wall span: **19.410 minutes**;
  peak **12 optimization workers**, CPU-only.
- Summed overlapping optimizer wall durations:
  **41.103 minutes**.
  Worker-count times wall duration is **2.740180
  worker-hours**, not measured CPU hours. Historical actual CPU time/RSS were not
  instrumented; parent/probe/grader work is not included in that worker envelope.
- Recorded surrogate propagation: **12 probes**,
  **297.974 summed wall-seconds**,
  excluding reference preparation and overlapping other work.
- One actual official grade: **559.210 seconds**.
- Extra confirmation, including boundary identification: **159.153
  wall-seconds**, **80.427
  measured CPU-seconds**, peak RSS **122.547 MiB**.

Machine-readable details: `compute.json`, `boundary_identification.json`,
`extra_selected_cases.json`, `extra_refinement.json`, `extra_refinement.log`.
Original control, evaluation and frozen evaluator hashes were checked before and
after refinement; all original manifest files were unchanged during that check.
The subsequent metadata-only clarification is recorded separately above.

Reproduce the extra checks from this directory, without changing the control:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /usr/bin/python3 -I -B extra_refine.py
```
