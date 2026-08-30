# Private evaluator

Only `participant/` is public. Never copy `hidden/`, `attempts/`, `champions/`,
`adversary/`, or `status.json` into a participant sandbox. Run from this concept:

```sh
python evaluator/evaluate.py --submission participant/workspace --report attempts/submission_report.json
```

The evaluator imports `Sandbox` from the task parent's `authoring/sandbox.py`.
There is no direct-subprocess fallback for untrusted code. Bubblewrap's network
namespace requires an **escalated outer evaluator command** in the builder's
restricted environment. Missing helper, failed namespace setup, timeout, malformed
output, or corrupted private reference assets fail closed with a reason.

For each case a temporary directory contains only its public JSON. The helper
mounts participant and submission read-only at their original paths and at
`/participant` and `/submission`, that directory at `/input`, and scratch at
`/output`. Python runs as `/usr/bin/python3 /submission/solve.py --input
/input/case.json --output /output/result.npz`. No hidden path is mounted.

`LimitedSandbox` only tightens the supplied helper: 60s wall/CPU, 2 GiB virtual
memory, single-CPU affinity, bounded file
sizes, and no network. `/tmp` is redirected into the same scratch mount so scratch
accounting includes both paths. Scratch plus diagnostics is checked every 20ms
and after exit against 256 MiB; this is a monitored limit, not a filesystem quota.
There is also a 4096-entry scratch limit. Logs go to a bounded file outside the
submission mount; at most 2048 diagnostic bytes enter the report. Solver processes
are killed before output inspection. The supplied helper controls isolation;
no claim is made that this Python wrapper replaces a production cgroup/seccomp
resource supervisor. In particular, the parent should retain its trusted outer
resource supervisor when deploying the benchmark.

NPZ parsing rejects symlinks, nonregular files, oversized files/uncompressed
members/headers, extra members, object arrays, malformed shapes, nonfinite values,
and nonzero inactive sites before scoring. Energy and gradient are recomputed
in `independent.py`, which never imports or executes participant code. Its
real-coordinate edge-list calculation is independently tested against the public
complex-stencil API. Reference fields, their energies, and SHA-256 digests are
checked every run. Submitted metadata cannot influence scores or runtime.

`hidden/calibrate.py` executes only builder-authored solvers on private cases;
it is not an entry point for evaluating untrusted artifacts. `hidden/freeze.py`
selects already-attained witness fields and writes the immutable manifest once.
`test_model.py` and `test_evaluator.py` are local scientific/scoring/parser tests.
`attempts/` retains measured runs and histories, including unsuccessful controls.
