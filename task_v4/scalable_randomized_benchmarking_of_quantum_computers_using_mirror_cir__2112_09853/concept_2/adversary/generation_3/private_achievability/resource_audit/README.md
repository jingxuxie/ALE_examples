# Generation 3 CPU-accounting infrastructure correction

This is an infrastructure correction, not another generation or hardness ratchet. The original 2,000-shot model, priors, hidden benchmark seeds, fixed targets, quality thresholds, and per-process limits remain unchanged. Main confirmed attempt v3 had finished and archived the original frozen task before authorizing promotion. This worker did not read or score v3.

## Provenance

- Original immutable task: `adversary/generation_3_snapshot_before_cpu_repair/`.
- Original manifest SHA256: `35ede7981b1fbe3beb7aff3e09fa4c0cd5ea4de05a293814b7823d2d1175fd72`.
- Corrected manifest SHA256: `7affbae62ca2b5e052b88be28fa714528cb3bb2c4cbd9bfd0efc08c4d7d9fced`.
- `promotion.patch` is the exact applied ten-file `apply_patch` patch. `promotion_provenance.json` remains the original prepared, not-yet-promoted record; `promotion_audit.json` records completed promotion and validation.
- Neither attempts, champions, snapshots, nor root `status.json` is edited by this repair.
- Promotion is complete: `promotion_audit.json` has `promoted: true`. Primary-source root-cause references and final handoff are in `source_provenance.json`; `cleanup_audit.json` verifies all 69 recorded episode groups are gone and all nine recorded transient services are inactive/collected. No additional worker or service stop was needed.

## Old failure and corrected accounting

The original transport's outer bubblewrap `RUSAGE_CHILDREN` counter omitted real descendant CPU. `runs/real_aggregate_bwrap/report.json` preserves a valid two-worker run with 62.207089 seconds of trusted probe self-CPU but only 0.175025 seconds reported by the original evaluator. The old separate aggregate test mocked the CPU counter. The original 56 physics/protocol checks did not test actual multiprocess CPU enforcement; earlier descriptions overstated that coverage.

The corrected trusted evaluator automatically re-executes through a uniquely named transient user service when its current cgroup is not user-owned and writable. This host provides a user bus and writable service cgroup under `user@2020.service/app.slice`. Each episode gets its own UUID child cgroup. The evaluator stays outside it; the bwrap child joins before policy launch. Parent-held close-on-exec descriptors read kernel `cpu.stat` and clean up only that owned episode group. The isolated policy sees neither cgroup filesystem nor user bus. Kernel accounting includes forks, threads, and workers auto-reaped with ignored SIGCHLD or SA_NOCLDWAIT. Missing counters or failed cleanup fail closed.

The original 60-second aggregate CPU limit, 0.25-second accounting tolerance, 90-second episode wall limit, and per-process RLIMITs remain. No CPU quota, aggregate memory cap, or new process-count restriction is introduced. Launcher RSS is diagnostic, not an aggregate-memory measurement. Explicit unsafe audit development still works without systemd or cgroup filesystem, labels its CPU estimate inexact, and never certifies a pass.

## Validation records

- `promoted_cli_selfcheck_report.json`: all 56 checks passed through the promoted CLI's automatic service bootstrap.
- `promoted_cli_baseline_report.json`: all 12 frozen episodes valid; average/worst `0.13310665517831277 / 0.10894424774926101`, exactly unchanged.
- `promoted_resources_report.json`: nine real subprocess cases on the promoted code, including ordinary forks, exec, orphans, SIGCHLD ignore, SA_NOCLDWAIT, and three real aggregate-CPU overruns. Exact source hashes accompany the result.
- `promoted_audit_report.json`: actual promoted public development imports and CLI work inside an outer bwrap without cgroup filesystem or user bus; unsafe audit cannot certify and strict mode fails closed there.
- `cgroup_boundary_report.json`: counter-path and inherited-descriptor denial, detached orphans, threads, and repeated auto-reap overrun. Reused only after comparing its recorded runtime hashes to the promoted files.
- `staged_cli_baseline_report.json`: retained failed staged run. One killed group did not empty within the five-second cleanup allowance; the cause is not established. No code was changed between this run and the completely valid promoted baseline. This is infrastructure evidence, not a hardness finding.

Historical generations 1/2 and earlier private G3 CPU fields based on outer `RUSAGE_CHILDREN` are inexact, not aggregate certificates. Main reports no process-creation calls in the delivered G1/G2 Python/C++ sources and maximum episode walls of 37.06/49.42 seconds. Those observations do not retroactively create kernel CPU measurements. Historical raw records and core scores are untouched.

## Selected private 2,000-shot policy

The already-selected policy is `adversary/generation_3/private_achievability/policies/family_portfolio/policy.py`, with its adjacent dependencies. It is unchanged since selection and was not tuned after viewing the fixed-suite result.

`family_portfolio_official_cgroup_report.json` is its actual corrected official bwrap/cgroup evaluation: all 12 episodes valid, **average 0.41068815580496776, worst family 0.33151134307583635**, accuracy targets not met. Maximum measured aggregate CPU is 28.497499 seconds. Its independent 24-case confirmation was 0.4262856900899512 / 0.338483844937249, versus 0.3709446745411399 / 0.30826237667156575 for the matched budget-adapted G2 control. The earlier confirmation's CPU fields carry the historical caveat above.

This private search demonstrates improvement over its control and the weak baseline, but **does not demonstrate achievability** of the unchanged 0.5 / 0.3902439024390244 thresholds. Achievability remains unknown from this private search; no impossibility claim is made. The search is closed and no further task generation is planned. `selected_policy_official_outcome.json` contains the final machine-readable result.

## Commands

Run from the `concept_2` directory, on the trusted host with `/usr/bin/bwrap`, a working user systemd bus, and a writable owned service cgroup:

```sh
/usr/bin/python -B evaluator/evaluate.py --self-check --isolation bwrap --report adversary/generation_3/private_achievability/resource_audit/recheck_selfcheck.json
/usr/bin/python -B evaluator/evaluate.py --submission participant/baseline --policy policy.py --isolation bwrap --report adversary/generation_3/private_achievability/resource_audit/recheck_baseline.json
/usr/bin/python -B evaluator/evaluate.py --submission adversary/generation_3/private_achievability/policies/family_portfolio --policy policy.py --isolation bwrap --report adversary/generation_3/private_achievability/resource_audit/recheck_portfolio.json
```

Main alone scores the unchanged deadline v3 submission:

```sh
/usr/bin/python -B evaluator/evaluate.py --submission attempts/v_3/submission --policy policy.py --isolation bwrap --report adversary/generation_3/v3_corrected_official_report.json
```

Public non-certifying development remains available without a cgroup-capable host:

```sh
/usr/bin/python -B participant/workspace/develop.py --submission participant/baseline --policy policy.py --isolation audit --family local_clusters --shape 4x4
```

The private resource harness requires an owned service cgroup. Run it with `systemd-run --user --wait --pipe --quiet --collect --property=TasksMax=infinity`, a unique unit name, the concept directory as working directory, and `/usr/bin/python -B <absolute-resource-audit-path>/promoted_validation.py --suite resources`. Audit compatibility uses the same script with `--suite audit` directly. Preserve existing reports when rerunning. `record_promotion.py` verifies all final source hashes and report assertions before writing the completed audit metadata.
