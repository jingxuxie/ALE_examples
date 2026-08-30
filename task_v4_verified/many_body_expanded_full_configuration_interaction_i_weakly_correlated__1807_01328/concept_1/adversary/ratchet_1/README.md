# E2 standalone packet — private administrator entrypoint

Only `participant/` is solver-facing. Do not expose this root, `evaluator/`,
hidden labels/models, provenance, prior attempts/champions, source witnesses,
or the cancellation study to a fresh solver. Stage only `participant/` and a
new empty submission workspace. No fresh agent has been launched.

The self-contained packet fixes the validated diversified/permuted 120-system
suite, preserves the original 36 practice assets and original weak baseline,
and declares a conditioned, non-IID six-stratum effective seniority-zero domain.
Public coefficient bounds are rounded enclosing bounds, not hidden coefficients.
No prior champion, witness file, learned model, or search code is included in
the solver-facing assets. The private source provenance contains hashes and
generation metadata, not a copy of an old solution or original witness file.

## Contract

Overall RMSE <=10 microhartree and every stratum <=25 microhartree; 160 query-cost
units per system; maximum queried space six virtuals; 120 aggregate CPU seconds;
2 GiB memory; 128 MiB submission. One persistent controller handles all 120
systems. The wall allowance is explicitly **600 seconds** for E2, declared
before a fresh launch. Only the wall allowance is relaxed; aggregate descendant
CPU/RSS enforcement, query limits, and accuracy thresholds are retained.

This packet's wall600 reference evaluations are official E2 evaluations, not
relaxed-wall diagnostic replays of E1. The original E root and champion remain
unchanged. Runtime requires Linux with usable bubblewrap user/PID/network
namespaces, Python 3.10 or newer, NumPy, and SciPy. Strict isolation is mandatory;
if an outer sandbox blocks namespaces, request host execution rather than
removing bubblewrap or the trusted PID-1 resource supervisor.

## Verification and reference commands

From this packet root:

```bash
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 evaluator/verify_freeze.py
python3 evaluator/evaluate.py --submission participant/baseline --output /tmp/e2_baseline_recheck.json
python3 evaluator/evaluate.py --submission ../../attempts/v_1 --output /tmp/e2_original_champion_recheck.json
```

The last command references the unchanged original champion outside this packet
only for privileged benchmarking; that directory must never be staged for a
fresh solver. Arbitrary new submissions use the same evaluator command with
`--submission SUBMISSION --output SCORE.json`.

Before freezing, the self-contained checks are:

```bash
python3 evaluator/validate.py
python3 evaluator/protocol_tests.py
python3 evaluator/resource_tests.py
```

These checks write private reports. Do not overwrite their frozen reports during
a later audit; `verify_freeze.py` is read-only, and benchmark rechecks above write
outside the packet. No generation/search tool or source repository is needed to
evaluate this fixed suite or run its independent checks.

## Private readiness records

Official E2 pre-fresh benchmarks on the same fixed 120 systems:

| Reference policy | Overall RMSE (microhartree) | Worst-stratum RMSE (microhartree) | True CPU (s) | Wall (s) | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Original weak baseline | 58.053588 | 116.748775 | 0.236011 | 9.130312 | valid accuracy failure |
| Unchanged original E champion | 49.417750 | 113.061401 | 104.073504 | 129.787099 | valid accuracy failure |

All 156 complete hidden/practice CAS tables and 1,134 independent
diagonalizations pass validation. Maximum independent energy discrepancy is
1.999e-15 hartree and maximum eigenpair residual is 8.180e-16. Protocol/isolation
and aggregate descendant CPU/RSS/wall regressions pass. The reference policies
consume at most 160 query units per system. These are accuracy failures, not
wall-only failures. No passing policy is currently measured.

The original champion includes process-CPU-dependent fit gates, so this E2
replay need not have bit-identical estimates to the earlier wall180 run on the
same suite. The fixed models/tables and accuracy/CPU/query limits are unchanged;
each actual measured score is retained separately rather than substituted.

- `status.json`: readiness, zero fresh attempts, no hardness claim, known-passing
  policy only if measured.
- `freeze_manifest.json`: pre-fresh SHA256 freeze, including a nine-file public
  allowlist; verified by `evaluator/verify_freeze.py`.
- `evaluator/hidden/target.json` and `target_diff.json`: full E2 contract and the
  explicit E1-to-E2 domain/suite/wall changes; deterministic limits unchanged.
- `evaluator/hidden/provenance.json`: fixed suite hashes, original source hashes,
  generation seeds, selection rules, and private clustering disclosure.
- `evaluator/hidden/validation.json`, `protocol_validation.json`, and
  `resource_validation.json`: independent numerical, isolation, and descendant
  resource-enforcement results.
- `evaluator/hidden/baseline_score.json`, `original_champion_score.json`, and
  `benchmark_summary.json`: actual complete-batch resource-accounted benchmarks.
- `evaluator/hidden/public_asset_audit.json`: original-practice/baseline byte
  equality and absence of prior solution/search assets from the public allowlist.

Failing reference policies do not establish impossibility or general hardness.
The conditioned suite contains two seed-derived neighborhoods, including a
tightly clustered author subgroup; detailed private diversity statistics are
retained in `evaluator/hidden/source_diversity.json`. No independent-witness or
IID-performance claim is made. Readiness is permission to consider a later
fresh launch, not a claim that no passing solution exists.
