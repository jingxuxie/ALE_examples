# Builder calibration and frozen release

Status: **builder_verified_achievable**. No fresh model sessions were run.

## Exact target

Thresholds fixed at `2026-08-27T22:55:23-07:00`; references frozen at `2026-08-28T06:15:47.400620+00:00`.
Case score is `clip((B-E)/(B-W),0,1)`. Core is the equally weighted mean
of three equally weighted two-case families. Pass: core >= 0.65, worst
family >= 0.45, every case valid, gradient RMS <= 0.002, no regression
beyond `1e-8*max(1,abs(B))`, and all resource limits met. Limits are 60s
wall/CPU, one core, 2GiB, 256MiB scratch, 4MiB NPZ. Runtime score is
`mean(max(0,1-wall/60))`, separate from quality. Full precision and
SHA-256 hashes are in `hidden/manifest.json`; do not update them after launch.

| Case / family | Baseline B | Witness W | Gap B-W |
| --- | ---: | ---: | ---: |
| h01 / strong_pinning | -865.182789168352 | -867.193469002612 | 2.010679834259 |
| h02 / strong_pinning | -1042.845984016759 | -1047.056779530893 | 4.210795514134 |
| h03 / perforated | -1039.123111871425 | -1040.766429619063 | 1.643317747638 |
| h04 / perforated | -1181.549868629329 | -1184.121945977015 | 2.572077347686 |
| h05 / high_vortex | -904.866759123204 | -907.534203972017 | 2.667444848813 |
| h06 / high_vortex | -1084.694025946792 | -1088.415663410181 | 3.721637463389 |

## Measured algorithms

| Algorithm | Core | Worst family | Runtime score | Passed |
| --- | ---: | ---: | ---: | --- |
| Public baseline | 0.000000000 | 0.000000000 | 0.958280385 | False |
| Plain L-BFGS multistart | 0.629914455 | 0.184733008 | 0.085437014 | False |
| General vortex portfolio | 0.786754289 | 0.567676538 | 0.082505046 | True |

All three rows use real sandbox execution. Portfolio/control cases were
calibrated concurrently in six independent sandboxes, each under the same
per-case limits; the official baseline CLI was also run end-to-end sequentially.
The general executable is `../champions/in_budget/solve.py` with its sibling
`portfolio.py`. No case IDs, lookup tables, or hidden fields are used.
Measured portfolio wall range: 54.668–55.194s per case.
Measured baseline wall range: 1.619–3.314s per case.

The 150-second offline searches supply attained witness fields. Stored
witnesses score 1.0 on energy by construction, but do not establish a
60-second solver result. Their runtime/pass fields are deliberately null
in `../attempts/witness_feasibility.json`. Ground states remain unknown.

## Nonconvexity and validation

The hidden suite has 6,440–9,228 real field variables, seven-hole grains,
strong pinning, and high-field cases with approximately 130–144 occupied
full plaquettes in the checked baseline fields. Many independently
converged local minima remain at distinct energies; histories and
gauge-covariant vorticity diagnostics are retained in `../attempts`.
The failed multistart control completes 35–72 starts/case in its offline
54-second audit and fails badly on the perforated family. This is not
merely unfinished local descent or evaluation of an analytic formula.

Sixteen unit tests pass: finite differences, gauge covariance, physical
flux and positive stiffness, uniform zero-field minimizer, independent
energy/gradient agreement, boundary masks, score and resource gates,
NPZ abuse, and immutable reference corruption checks. The real sandbox
baseline smoke test and all-six baseline CLI also pass output validation.
Maximum hidden directional-derivative relative error: 3.66e-08.
Maximum independent gradient disagreement: 1.42e-14.

Only `participant/` is public. Private scripts, seeds, calibration fields,
references, algorithms and reports remain outside it. Scratch is monitored
rather than quota-mounted; keep the trusted parent resource supervisor.
