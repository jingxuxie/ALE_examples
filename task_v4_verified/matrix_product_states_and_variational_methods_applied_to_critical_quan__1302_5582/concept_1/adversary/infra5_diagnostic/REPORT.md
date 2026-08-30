# Bounded infra5 diagnostic: inconclusive non-reproduction

Completed 2026-08-28T20:16:40.113768+00:00. **Exactly three runs; stopped.** No retries, fresh agents, official regrades, physical energy/quality checks, target changes, or original-file edits.

## Case and unchanged limits

All three calls use `g1_ea6c7b33ae689d1cfeeec166ffd0a4a0`, the existing odd-short request, with the complete byte-identical v3 submission. CPU6 / protected wall30, child kernel soft8/hard9, inherited outer soft10/hard11, and the150-second operational watchdog are unchanged. Memory, output-file and4096-byte protected-accounting limits are also unchanged. Submission/public staging is hash-checked and mounted read-only; only feature inputs reach the sandbox, not the private reference event or hidden labels.

## Protected execution measurements

Seconds, directly from the protected parent wait4 report. All runs exit normally, with no timeout.

| Trial | Child user CPU | Child system CPU | Child total CPU | Protected child wall | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 5.086168 | 0.409651 | 5.495819 | 6.177131 | 0 |
| 2 | 4.678390 | 0.844312 | 5.522702 | 5.764245 | 0 |
| 3 | 5.032252 | 0.370839 | 5.403091 | 6.455360 | 0 |

These are diagnostic process/resource observations, not scientific grades.

## Trusted phases and parent CPU

CPU columns are cumulative child user+system usage. Wall columns are measured from protected parent spawn time. Parent CPU is separately measured over supervision and is **not** added to solver CPU.

| Trial | CPU before RLIMIT | Wall before RLIMIT | CPU before runpy | Wall before runpy | Parent interval CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.198546 | 0.299478 | 0.293395 | 0.399471 | 0.194011 |
| 2 | 0.046380 | 0.051209 | 0.700623 | 0.771894 | 0.001806 |
| 3 | 0.111196 | 0.155424 | 0.278602 | 0.436389 | 0.044444 |

The inherited limits are10/11 at the early and pre-RLIMIT markers; post-RLIMIT, pre-seccomp-load and pre-runpy markers all record8/9. All five expected phase messages are present, finite, and tied to the staged instrumented worker. Raw user/system components, process clocks, timestamps, parent before/after values, exit status and report hashes are retained per run.

| Trial | CPU around RLIMIT setter | CPU pre-seccomp-load to runpy | System CPU in that interval |
| --- | ---: | ---: | ---: |
| 1 | 0.081148 | 0.011987 | 0.011987 |
| 2 | 0.071024 | 0.365099 | 0.364530 |
| 3 | 0.000062 | 0.166403 | 0.166403 |

The seccomp interval also contains filter release, tiny trusted setup and measurement work; it is not a kernel-only profiler. Phase messages travel over a bounded blocking pipe while still in trusted bootstrap. The child closes the writer before runpy. The nondumpable parent retains the messages and writes its inode-checked, preopened terminal report after reaping the child. There is no mutable-marker authority or polling loop. Each resource report remains below4096 bytes and passes the original accounting predicate plus the diagnostic phase/version/hash checks.

## Interpretation

**The17.117624-second anomaly did not reproduce. Attribution remains inconclusive.** The three totals are5.403091–5.522702 CPU seconds. Trusted pre-user CPU varies0.278602–0.700623 seconds, predominantly system CPU; the seccomp boundary varies0.011987–0.365099 CPU seconds. This confirms a variable initialization contribution in the probes, not its responsibility for the historical spike.

The preserved original short report has CPU17.117624, child wall18.29138640803285, return137, and no timeout flag. Its generic CPU-limit error classifies eligibility, not the exact kill cause. These three measurements do not explain why that historical total exceeded hard9, establish that the harness is correct, diagnose a solver defect, or supply hardness evidence. Instrumentation itself adds work and a passed descriptor and may perturb startup/spawn timing. The total-minus-pre-runpy residual includes user imports, state output and termination as well as computation.

## Preservation and quiescence

All **259 pinned original files** remain unchanged, including the accepted reports, original runtime/frozen assets, the complete199-file v3 submission and16-file participant surface. Instrumented code still matches its pre-execution launch manifest. The original production runner's ephemeral `/tmp` placement was retained to avoid changing source-I/O placement; all three temporary trees were removed, and all retained artifacts are inside this directory.

Host snapshots at2026-08-28T20:09:02.954682+00:00 and2026-08-28T20:09:16.254278+00:00 find all three outer PIDs absent and no matching launch groups, working directories or open diagnostic descriptors. Run-artifact hashes remain identical across the12-second observation interval. These are bounded observations: inaccessible/vanished proc entries are recorded, not treated as exhaustive process attestation.

## Artifacts and stop condition

- `launch_manifest.json`: case/limit/source freeze and259 original pins.
- `original/`: exact original worker/runner copies; `runtime/`: instrumented copies; `run_diagnostic.py`: single-use three-call driver.
- `request.json` and `reference_event.json`: exact feature request and preserved original short-report context; the reference is never mounted into solver sandboxes.
- `runs/trial_1/`, `runs/trial_2/`, `runs/trial_3/`: raw protected resource/phase JSON, process and staging reports, output states/logs and per-run hashes.
- `results.json`, `analysis.json`, `execution.json`, `checkpoint.json`, and `artifact_manifest.json`: complete observations, attribution limits, stop record and retained-file inventory.

**No additional diagnostic run is performed or scheduled.** `runs/` already exists, so the driver refuses a repeated invocation. No new generation is awaited.
