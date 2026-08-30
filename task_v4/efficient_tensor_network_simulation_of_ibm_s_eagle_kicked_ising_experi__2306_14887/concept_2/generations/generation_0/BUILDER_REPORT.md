# Builder handoff: ready for a fresh attempt

## Frozen task and scope

- Mode B: counterexample/falsification of the supplied observable-spread heuristic.
- Circuit: 12-cycle, all-zero initial state, global Rx followed by fixed positive pi/4 ZZ on every edge.
- Public control: six interpolated knots, depth 12–48, knots 0.12–1.45, maximum slew 0.12 radians.
- Observable: spatially averaged nearest-neighbor ZZ. Actual normalized OBC MPS at chi 4, 8, 16; exact closing-edge MPO, no BP or swap approximations.
- Five families: nominal, offsets ±0.002, and linear tilts ±0.002. All must have spread ≤0.008 and error ≥0.15.
- This is not a falsification of arXiv:2306.14887. The original paper distinguishes bond convergence from uncontrolled BP loops and also discusses MPS truncation errors.
- Target SHA-256: `4b5a7ea5308eb3fd0134cd8684764f655f1145f73e07e7d6bd83524f77026e30`. Freeze timestamp: 2026-08-28T17:34:59.217370+00:00.

## Package boundary

Expose **only `participant/`** to the fresh solver. Its required layout is
`TASK.md`, `input/`, `workspace/`, and `baseline/`. Keep `evaluator/`, `attempts/`,
`champions/`, `adversary/`, and root builder-development files private. The
host must enforce this boundary; `exposure.json` documents it, not implements it.
The root `TASK.md`, `input/`, and `workspace/` are retained builder-development
copies and are not the participant entrypoint.

Run the host checker from the concept directory:

```bash
python -I evaluator/evaluate.py --submission DIRECTORY --output JSONPATH
```

Only `witness.json` is consumed. The checker independently evolves the exact
bit-pair statevector, evolves the frozen MPS snapshot, and independently measures
ZZ by bitwise domain-wall counting. It never imports submission code and uses
neither participant simulator files nor public input at grading time.
Outputs include `valid`, `passed`, `core_score`, `worst_family_score`,
`resource_score`, measured `elapsed_seconds`, diagnostics, and `reason`.
`resource_units` counts MPS layers across families and caps, not FLOPs.

## Measured feasibility and baseline

| Artifact | Core | Worst family | Resource | Pass |
|---|---:|---:|---:|---|
| Private builder champion, depth 36 | 100.000000 | 100.000000 | 33.333333 | yes |
| Packaged 48-trial baseline, seed 14887 | 60.163075 | 48.694114 | 27.906977 | no |

The private champion's minimum family error is **0.160714327834** and maximum
spread is **0.005036439252**. Exact nominal ZZ is
0.262075869863, whereas its MPS estimates are
[0.42847890311053966, 0.4332740447277924, 0.43188163603926083]. This is a finite physical bias,
not an artificial zero observable. The champion and provenance are preserved in
`champions/builder/`, outside the participant tree. Its truncation diagnostics
are substantial: they explicitly do not justify a rigorous accuracy certificate.
The supplied heuristic intentionally disregards those diagnostics.

The baseline command is `python participant/baseline/search.py --submission
attempts/participant_baseline --trials 48 --seed 14887` (one shell line).
Its report is `attempts/participant_baseline/evaluation.json`. Packaging preserved
all baseline scores and every family result exactly.

## Audits

- **56 scientific checks pass**: independent bit-pair and dense-Hamiltonian exact evolution; unitarity; zero and Clifford cases; chi-64 full-state agreement; independent magnetization and ZZ; transfer contraction; both LAPACK SVD drivers; and the champion's five families at chi 64.
- Maximum reported scientific check error: 1.81e-13. See `attempts/final_self_check.json`.
- **23 integrity checks pass**, including malformed/duplicate/nonfinite/oversized artifacts, forbidden physical controls, symlinks, poisoned submission modules/CWD/PYTHONPATH, and public/hidden snapshot equality. See `attempts/evaluator_audit.json`.
- Exact Schmidt degeneracies receive deterministic subspace bases at every cut, including fully retained groups; this removes LAPACK-dependent gauge choices. Both SVD drivers agree far below scoring margins.
- Decimal rounding to 10 and 12 places preserves passing scores. Four of five additional independent ±1e-4 per-knot perturbations also pass all families; one has maximum spread 0.00942747 and fails the 0.008 condition. This extra probe is recorded, not hidden or silently converted into a grading requirement. The witness is robust to the five specified families, **not certified throughout a continuous neighborhood**.

## Readiness

A private passing witness exists. No fresh model was run, no delegation was
used, and hardness has not been measured. The main runner owns the one-hour
fresh attempt and final hardness/status decisions. Do not expose privileged
search logs or the champion as hints. `status.json` marks the package ready,
not tournament success. `freeze_manifest.json` hashes all participant assets
and trusted checker sources/snapshots before the fresh attempt.
