# Pre-launch CPU-accounting correction

The first generation-2 draft measured RUSAGE_CHILDREN outside bubblewrap's PID
namespace. That counted the namespace supervisor, not the full prediction CPU
cost. The archived `cpu_accounting_v0_*.json` records are invalid for resource
scoring and are not used in any hardness decision.

The corrected evaluator mounts a read-only trusted launcher in the isolated
namespace. That launcher starts and reaps the prediction process, measures its
user-plus-system CPU time, and returns a private accounting record on its own
stdout. Submission stdout is separately captured and cannot replace this record.
No held-out labels enter the namespace. A known two-CPU-second workload reports
2.357285 seconds including interpreter/import/I/O work. The corrected optimized
incumbent costs 8.70568 seconds, while the native fast predictor costs 2.239594
seconds for the same 200,000 events. The frozen target remains 2.4 seconds.

This correction occurred before any generation-2 participant attempt. The
original generation-1 evaluation used wall time and is unaffected. Prior-agent
source and binary artifacts remain private; only the original weak regression
baseline is supplied to generation 2.
