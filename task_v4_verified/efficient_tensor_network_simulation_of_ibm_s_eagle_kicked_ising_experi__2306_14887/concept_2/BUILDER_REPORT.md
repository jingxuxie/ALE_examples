# Generation 1 launch handoff

Frozen 2026-08-28T18:42:43.634845+00:00. **READY / unknown_achievability**. No launch blocker;
no passing reference is known for the strengthened target. This is not a hardness
finding. Only main launches fresh v2 and assigns hardness after its outcome.

## Frozen task and exposure

Only `participant/` is solver-visible. Its concise `TASK.md`, `input/target.json`,
`workspace/` simulator and protocol, and independently authored `baseline/` are
current. Root `TASK.md`, `input/`, and `workspace/` are private legacy generation-0
builder files, not the participant contract. Private previous submissions and
builder witnesses remain outside participant. The runner enforces the allowlist;
`exposure.json` is documentation, not an OS sandbox.

Target SHA-256: `6fa4aba2f0f0207c3882ac10dbc227d3f901fd27964085db1dd8eabdeac331ef`.
The six independently biased control knots have zero drift or one of all 64
sign corners at +/-0.002 radians. Every drift is crossed with the original five
perturbations, giving **325 waveforms**. Every waveform must satisfy exact error
>=0.15 and successive-cap spread <=0.008 for chi 4,8,16. The witness schema,
12-cycle all-zero kicked-Ising dynamics, observable, nominal knot bounds, depth,
slew, and actual pulse constraints are unchanged. Every realized waveform is
physically validated. This is a finite-suite certificate, not certification of
all points inside a continuous box. It stress-tests the supplied finite-bond
convergence heuristic, not the original paper or its uncontrolled BP loop errors.

## Preservation and scientific rationale

`generations/generation_0/` archives the exact original participant, evaluator,
status, freeze, exposure, builder report, selected evidence, and private champions;
`archive_manifest.json` records their hashes. Original attempt/log directories were
not relocated. `attempts/v_1_score.json` and `attempts/frozen_v_1/` are unchanged.
`champions/generation_1/` is the exact 23-file original fresh submission copy.
The first attempt remains a generation-0 success: depth24, 100/100, resource50,
1232.76 seconds reported by main. The archived grader replays 100/100.

The authorized drift scale comes from the prior privileged calibration sweep,
not changed acceptance thresholds. Smaller surveyed scales through 0.001 did not
break the fresh witness; 0.002 knot corners cause genuine convergence-spread
failures while exact dynamics, full-rank agreement, and numerical stability hold.
Original evidence is preserved in `adversary/generation_1/`. No additional private
optimization or fresh-model launch was performed during this ratchet build.

## Full-suite reference grades

All grades are physically valid, complete 325-waveform evaluations, and fail the
new all-family requirement. Resource score remains 1200/depth.

| Reference | Depth | Core | Worst family | Resource | Failed waveforms | Seconds |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 43 | 60.163075 | 28.308739 | 27.906977 | 325/325 | 82.14 |
| champion | 24 | 100.000000 | 89.490058 | 50.000000 | 14/325 | 40.19 |
| builder | 36 | 100.000000 | 84.690387 | 33.333333 | 20/325 | 60.23 |

The weak baseline artifact is byte-identical to the original independent baseline;
its original proposal loop is preserved. The runnable baseline screens using the
original five families, then verifies its selected witness on all 325. No private
solution coefficients, tuned seed, or champion-derived search enter participant.
Grade files and the baseline run report are in `attempts/ratchet_generation_1/`.

## Evaluator and audits

The checker reads only bounded `witness.json` data, rejects malformed artifacts,
and loads host-only target, protocol, simulator, and independent exact-oracle
snapshots. It never runs or imports submission code. The Linux checker defaults
to four trusted fork workers, each with one BLAS thread, with an enforced 600-second
wall budget. Timeout produces a nonpassing, incomplete result. Outputs include
`core_score`, `worst_family_score`, `resource_score`, `valid`, `passed`, `reason`,
`elapsed_seconds`, completeness, resource units, and family count.

All **141 checks passed**: physics76, contract23, integrity23, reference19.
Physics checks include independent exact and dense/bitwise references, unitarity,
zero/Clifford controls, independent observable evaluation, chi64 agreement,
selected corner families, and SVD-driver stability. All original physics function
ASTs are unchanged; the independent exact oracle is byte-identical to generation0.
Every one of the 325 fresh and builder results agrees with the pre-ratchet sidecar
reference. Public baseline diagnostics agree with the independent grader.
Contract and isolation checks include the complete Cartesian product, actual
waveform constraints, worker bound, enforced timeout, malformed/poisoned input,
archive identity, snapshot parity, and absence of private witness leakage.
Evidence: `physics_audit.json`, `contract_audit.json`, `integrity_audit.json`,
`reference_audit.json`, and `original_replay.json` under the run directory above.

## Launch commands

From this concept directory, host grading:

```bash
python -I evaluator/evaluate.py --submission DIRECTORY --output JSONPATH
```

From the participant directory, runnable public baseline:

```bash
python baseline/search.py --submission submission --trials 48 --seed 14887
```

`freeze_manifest.json` hashes the current public assets and trusted checker.
`status.json` records readiness, unknown achievability, grades, audits, and main's
ownership of subsequent fresh attempts. No passing reference is needed to launch.
