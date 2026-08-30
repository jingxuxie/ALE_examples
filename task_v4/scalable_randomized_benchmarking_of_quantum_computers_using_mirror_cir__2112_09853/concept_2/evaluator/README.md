# Trusted evaluator and integration

From the concept_2 directory:

```bash
OPENBLAS_NUM_THREADS=1 python -B evaluator/evaluate.py --submission participant --policy baseline/policy.py --report evaluator/hidden/baseline_report.json
OPENBLAS_NUM_THREADS=1 python -B evaluator/evaluate.py --self-check --report evaluator/hidden/selfcheck_report.json
OPENBLAS_NUM_THREADS=1 python -B evaluator/evaluate.py --submission /absolute/submission_directory --policy policy.py --report evaluator/hidden/attempt_report.json
```

The default is **required, fail-closed `/usr/bin/bwrap` isolation**. Nested
sandbox namespace failures require running the evaluator through the main
coordinator's approved escalation/runner. Do not replace isolation with same-
process imports. `--isolation audit --allow-unsafe-local` exists for trusted
diagnostics only, is explicitly uncertified, and can never return `passed=true`.

The private parent imports only frozen `evaluator/hidden/model.py` and
`evaluator/hidden/transport.py`. It snapshots submitted regular files and runs
the policy with read-only `/submission`, read-only system Python libraries,
private PID and network namespaces, an isolated `/proc`, `/dev`, and writable
`/tmp`. Neither the host repository, evaluator files, seeds, environment secrets
nor the parent's `/proc` namespace are mounted. Each episode restarts the
process. Stdout is a bounded strict JSON-lines channel; stderr is bounded.
Source/benchmark hashes are checked before and after, and artifact/transcript
hashes are recorded. Python child limits bound CPU, address space, open files,
core dumps and file size; wall time is enforced by the parent.

**Main integration requirement:** launch fresh research agents with
`authoring/run_attempt.py`, `3600s`, `ultima-alpha`, high effort,
`--task-read-only`, exposing **only** `participant/` plus their designated
submission directory. The broader authoring filesystem is not a safe research
agent mount. Use the main allowlisted runner for evaluation. Bubblewrap here
protects the policy process, not the outer research agent. For hostile fork
bombs or aggregate multi-process memory exhaustion, the common runner should
add cgroup process/memory/CPU limits; rlimits alone are not aggregate cgroups.
Do not mount `attempts`, `champions`, `adversary` or `evaluator/hidden` for agents.

`hidden/freeze.py` is author-only and refuses to overwrite a frozen benchmark.
It establishes private independent seeds, fixed target hashes, source hashes,
and the immutable numerical thresholds. Seeds and private validation reports
must remain private. Public model/transport copies are conveniences, never
trusted evaluation imports. Changing them cannot change official truth.
