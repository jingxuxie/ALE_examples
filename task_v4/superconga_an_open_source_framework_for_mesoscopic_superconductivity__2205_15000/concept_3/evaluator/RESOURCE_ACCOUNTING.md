# Checker repair 2: whole-sandbox CPU accounting

This is a scoring-environment correction, not a new task generation. The original
90 CPU-second and 120 wall-second budgets, 56 observations, physics, prior,
hidden cases, participant tree, target and quality gates remain unchanged.
The generation-one archives and reports are historical and are not overwritten.

## Defect and repair

The original checker subtracted `os.times().children_*` around the shared
bubblewrap helper. On this host bubblewrap's ordinary early-exit notification
path did not propagate the submitted process's complete descendant resource
usage to that wait. Recorded CPU values often measured only wrapper overhead.
Wall time and reconstruction scores were not calculated by that broken counter.

The repair is confined to the evaluator. `resources.ResourceSandbox` subclasses
the unchanged paper-root `authoring/sandbox.py`; it preserves the helper's mounts,
fresh PID/network namespaces, environment, memory/file limits, and initial
single-core affinity. It additionally:

1. Sets both inherited `RLIMIT_CPU` values to **90**, not 93/95. Short-budget tests
   round that per-process kernel limit up to an integer; the aggregate checker
   still uses the requested fractional test budget.
2. Uses bubblewrap `--as-pid-1` with one standalone, read-only trusted reaper at
   `/__ldos_resource_guard.py`. No evaluator directory, scene, or seed is mounted.
   The guard forks the submission, waits for all children including adopted
   orphans, and only then exits with the submitted primary process's status.
   This avoids bubblewrap's earlier exit-notification accounting path.
3. Reaps the outer bubblewrap process with **per-process `wait4`**, not a global
   child-usage delta. For a clean accepted exit this is the authoritative total
   user plus system CPU of the sandbox tree, including setup and teardown.
4. Samples the live `/proc` tree about every 10 ms, including children of every
   thread, not only the leader. Each snapshot sums current process self CPU plus
   already-waited child CPU. It does **not** add historical dead-process maxima
   to parents' inherited child totals. PID start times and pidfds protect signal
   targets from PID reuse. A near-limit tree is stopped and rescanned before
   declaring aggregate exhaustion, avoiding a racing child-to-parent transfer
   being used as evidence of double-counted exhaustion.
5. Rejects a clean result whose final `wait4` total exceeds 90 even if the final
   burst occurred between samples. Silent busy clients are still sampled while
   the JSONL selector waits. The existing wall deadline, 64 KiB line/stderr bounds,
   and three-second post-final exit rule remain enforced.

## Accounting escape prevention

The trusted reaper disables dumpability before forking. An inherited libseccomp
filter on the **submitted subtree**, not the guard, prevents CPU-history loss:

- Changing `SIGCHLD` disposition is denied, so `SIG_IGN`/`SA_NOCLDWAIT` cannot
  auto-reap descendants without propagating their accounting.
- Non-thread `clone` requires the normal `SIGCHLD` exit signal. `clone3` returns
  `ENOSYS`, allowing libc's conventional clone fallback. Normal forks, waits,
  Python threads and the tested NumPy/SciPy workloads remain functional.
- New namespaces via clone/unshare/setns are denied. Nested namespace teardown
  must not discard descendants before a trusted wait.
- Affinity changes are denied after the helper pins one CPU; ptrace,
  process-memory writes and pidfd-fd extraction are denied to protect the reaper.

These are enforcement restrictions, not a different inverse problem. Code that
requires a custom `SIGCHLD` handler, unusual clone semantics, nested namespaces,
or repinning is not supported by this repaired checker. Compilation and normal
subprocess execution remain possible; `/tmp` and `/output` remain writable and
submission/participant mounts remain read-only.

Missing bubblewrap, libseccomp, pidfd support, required proc counters, or a usable
consistent near-limit snapshot causes failure, never unsandboxed execution or a
wall-only replacement. Submissions never supply CPU evidence used in grading.
Self-reported CPU in test fixtures is only an independent workload cross-check.

## Precision and limits

- Linux CPU accounting and sampling are not instantaneous stopping. Proc counters
  on this host have 10 ms tick resolution, and there can be polling, scheduling,
  per-live-process tick truncation and termination latency. Aggregate CPU stopping
  is therefore approximate at the boundary; **no clean accepted result may have
  final kernel-accounted CPU greater than 90**. The strict per-process RLIMIT and
  the independent 120-second wall deadline are additional defenses.
- Forced namespace termination may prevent final child-usage propagation. Such
  episodes are already invalid. Their `resource_accounting.complete` is false;
  the reported sampled/confirmed CPU is diagnostic, not a falsely exact final
  total. The exact `final_wait4_cpu_seconds` and the sampled fields are retained
  separately. Non-quiescent sampled peaks can contain transient races and are not
  used to reject on their own or to charge a clean result.
- Tree enumeration is capped at 4096 processes and fails closed above it. This is
  not a cgroup implementation and does not claim delegated aggregate memory
  accounting. The unchanged helper's address-space limit remains per process.
- The evaluator's own trusted forward-table computation is outside submitted CPU
  usage, as before. Sandbox setup/reaper overhead is inside the charged tree.
- Scheduling throughput still varies; neither CPU accounting nor a 120-second
  wall cap promises identical optimizer iterations on every host/core.

## Validation and provenance

Run from `concept_3` in an escalated outer execution context:

    LDOS_SANDBOX_TESTS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s evaluator -p 'test_*.py' -v

`test_resources.py` covers a busy process, aggregate forked CPU, rapid short-lived
reaped children, orphaned grandchildren, children forked by a nonleader thread,
known NumPy eigensolver CPU, the exact 90/90 inherited RLIMIT, autoreap/affinity
escape rejection, a separate sleeping wall timeout, final CPU enforcement after
deliberately missed samples, and failure without an unsandboxed fallback.
Normal compiler subprocesses writing source in `/tmp` and a binary in `/output`
are also exercised.
Resource tests use a fixed public labeled scene, not evaluator hidden latents.

`attempts/checker_revision_2/` contains new reports and the final resource audit.
The initial failed development tests are retained: their tight overhead assertion
omitted measured bubblewrap/reaper setup cost, and two old metric fixtures needed
the newly reported CPU field. Neither issue involved reconstruction thresholds.
Setup CPU also varies across cores, so the final integration cross-check uses
the independent client-usage lower bound and the pinned-one-core wall upper
bound, not a fixed setup-cost allowance. A synthetic child-to-parent CPU transfer
test explicitly checks that reaped work is not counted twice.
`hidden/checker_revision_2.json` records repaired checker hashes and links the
unchanged original freeze, frozen scientific assets, shared helper and archived
champion. Original CPU fields are explicitly historical/undercounted, not silently
relabelled as valid aggregate measurements.
