# Resource enforcement audit

The initial target freeze predates an enforcement-only correction to evaluate.py:
submission execution is pinned to four allowed CPU cores using taskset. This
implements the already-published four-thread budget. No target, input case,
baseline cost, score formula, or validity condition changed. The correction was
made during the first fresh attempt, before reading any submitted solution or
running its hidden evaluation. The identical corrected evaluator is used for
baseline and fresh scores. Address space and CPU seconds are enforced per process;
the wall-clock watchdog and process-tree cleanup cover the entire job. This is
not a claim of cgroup aggregate-memory enforcement.

The 1.20 throughput target represents a substantial deterministic resource gain,
not a timing-noise improvement. Achievability is not assumed. The private closure
search is recorded as an offline gap probe, not a passing submission and not a
reference optimum.
