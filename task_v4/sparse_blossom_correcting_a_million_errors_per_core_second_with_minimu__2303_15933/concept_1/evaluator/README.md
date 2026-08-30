# Privileged evaluator handoff

Never expose this directory (including `evaluator/hidden/`), `attempts/`, `champions/`, `adversary/`,
or `status.json` to the fresh participant. Mount ONLY `participant/` and the
fresh output directory using the main runner's minimal filesystem allowlist.
The participant runtime uses `/usr/bin/python3`; the local dependency tree is
real files under `participant/input/runtime`, not links to `/home` or `/opt`.

Run from the ALE root, as the trusted task builder/main:

```
ROOT=tasks_v4/sparse_blossom_correcting_a_million_errors_per_core_second_with_minimu__2303_15933/concept_1
/usr/bin/python3 "$ROOT/evaluator/evaluate.py" --submission "$ROOT/participant/workspace/submission.py" --report "$ROOT/attempts/final_report.json"
```

**Run the evaluator with `exec require_escalated` in this environment.** Nested
`bwrap --unshare-net` under the outer tool sandbox fails with a netlink EPERM.
The evaluator fails closed; there is no unsafe direct-subprocess fallback.
Escalation does not remove the worker's inner isolation.

The trusted parent verifies hashes, copies only label-free syndrome NPZs into
the request mount, snapshots the submission, and starts `input/worker.py` under
`bwrap`. The sandbox has separate user, PID, network, IPC and UTS namespaces;
`/usr`, `/lib`, `/lib64`, `/bin`, `/etc` and participant/submission/request mounts
are read-only; only `/out`, private `/tmp` and `/dev` are writable. The host task
tree and parent `/proc` are absent. The parent never imports candidate code and
never deserializes pickle. Output archives have strict shape/type/size checks.

`input/API.md` documents the JSON/NPZ worker protocol. Main may replace only the
launcher with an equivalent independently audited sandbox; do not expose the
trusted evaluator just to let the worker import it. The public worker contains
no seeds, labels, thresholds or scoring logic.

CPU is measured using trusted `wait4` with `bwrap --as-pid-1`, not the candidate
response. The ordinary bwrap PID-1 helper was experimentally found to hide worker
CPU from the parent's rusage; `--as-pid-1` is mandatory. A parent-built seccomp
filter blocks clone/clone3/fork/vfork, ptrace and cross-process memory access.
Only one execution thread can exist, so descendants cannot evade CPU accounting.
Compile extensions during development, not during evaluation. The worker pins
itself to one available core and applies hard CPU, address-space, file-size and
FD limits. The wall watchdog is 900 seconds because the shared host can be heavily
oversubscribed. There is no dedicated cgroup here. A watchdog timeout is an infrastructure event
worth retrying once without changing the frozen target, not evidence of scientific
infeasibility. Six GiB is a process address-space cap, not a cgroup RSS quota.
The public worker and all scientific target/data checksums remain unchanged by
this launcher-only CPU-accounting correction, made before any fresh participant.

Standard report fields are `core_score` (fraction of baseline failures removed),
`worst_family_score` (minimum family removal fraction), and `runtime_score` /
`resource_score` (min(1, CPU budget / measured CPU)). `score` is 100 times
`core_score`. Negative accuracy scores are possible and intentional. `valid`
means the submission produced a conforming result; `passed` separately means
all frozen gates passed. `reason` explains invalidity or lists failed gates.
Candidate directories under `attempts/v_1`, `champions/<name>`, or
`adversary/<name>` are allowed; collection roots and actual hidden/evaluator
ancestry are rejected. Main must keep each candidate directory free of private
siblings because only that entire submission parent is copied into the sandbox.

`--split challenge` is development-only and cannot produce final success.
`--split both` performs final adjudication, including independent holdout.
Holdout reports remain privileged; do not use repeated holdout feedback to guide
the fresh participant. Baseline validation is not a fresh participant attempt.

`evaluator/hidden/frozen.json` fixes targets and checksums before the first fresh run.
Rebuilding frozen data is deliberately refused. Labels are independently sampled
from the public mechanism distribution, not assigned by any decoder.
