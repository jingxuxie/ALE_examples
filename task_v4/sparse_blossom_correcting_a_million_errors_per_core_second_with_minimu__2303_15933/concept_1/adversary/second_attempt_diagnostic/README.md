# Frozen v2 termination diagnostic

This is a bounded private diagnostic, not a new generation or a candidate update.
All persistent outputs remain in this directory. The actual participant,
evaluator, targets, status and candidate snapshots are never edited.

`run.py` verifies the full frozen v2 snapshot against main's pre-evaluation
hashes, then runs exactly one unchanged official evaluator replay. It next runs
one nonqualifying diagnostic using an in-memory evaluator wrapper: only the CPU
ceiling changes from 132 to 180 seconds (worker soft/hard RLIMIT_CPU: 133 to 181).
The original bwrap launcher, seccomp filter, network/PID namespaces, mounts,
worker, full hidden dataset, case order, scoring and wall watchdog remain in use.
The driver has a separate 1,000-second total bound and explicitly reports if it
terminates a run itself; such termination is not evidence of a candidate failure.

An external trusted monitor records only these evaluation process trees, CPU
counters, limits, and completed output filenames. It does not inject a signal,
change the candidate, alter scheduling, or feed information to it. The relaxed
run retains prediction NPZs and the worker's diagnostic response; resource
scoring still uses the original trusted parent wait4 measurement, not that
response. Parent temporary files and cache are placed inside this sidecar.

Raw reports: `official_replay.json`, `relaxed_diagnostic.json`, and `summary.json`.
Process observations are in `*_processes.jsonl`; integrity checks in
`integrity_before.json` and `integrity_after.json`. The relaxed report is always
explicitly nonqualifying, even if its numerical gates would pass.

Primary Linux documentation inspected August 28, 2026:

- https://man7.org/linux/man-pages/man2/getrlimit.2.html
- https://man7.org/linux/man-pages/man2/getrusage.2.html
- https://raw.githubusercontent.com/torvalds/linux/v5.15/kernel/time/posix-cpu-timers.c

`observe_clocks.py` additionally samples the evaluation worker's Linux dynamic
process CPU clocks from the trusted host, without executing code in that worker.
Upstream Linux 5.15 uses CPUCLOCK_PROF for RLIMIT_CPU, while its scheduling clock
is sampled separately. This is relevant to the observed Ubuntu 5.15 kernel but
is not, by itself, proof of the initial signal's cause. Raw clock samples are
kept in `cpu_clocks.jsonl`; PROF, VIRT and SCHED use Linux clock indices 0, 1, 2.

The CPU hard limit can produce SIGKILL. That does not establish that every
SIGKILL came from that limit; this experiment does not record the signal sender.
Process accounting and a completed same-source run are retained to separate an
actual measured overrun from an unexplained termination.
