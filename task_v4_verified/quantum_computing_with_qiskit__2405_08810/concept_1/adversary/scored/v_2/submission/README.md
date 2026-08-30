# Hardware-aware phase compiler

`solution.py` is the executable JSON-lines entry point. It serves multiple
workloads in one process and flushes each response. The submission is
self-contained: normal execution does not read the participant assets, use the
network, invoke another process, or create files.

## Method

The compiler represents every remaining symbolic term in the current reversible
Boolean basis. A native CX updates these coordinates exactly. Whenever a term is
a single basis row, its original symbolic rotation is emitted on that qubit.

The native search combines topology-sensitive spanning-tree potentials,
calibrated directed-edge costs, several independent search populations, and
prefix or pruning-and-repair mutations. Disconnected residual supports are
collected with native Steiner-tree operations. Reversing the construction
restores the identity Boolean map without ancillas or qubit relabeling.

Final optimization searches exact two-, three-, and four-qubit linear/phase
states. Each replacement preserves both the block's Boolean map and every
required symbolic parity. A dependency-respecting scheduler reorders commuting
operations to reduce the calibrated makespan. Candidate selection uses the
specified error-weight-plus-0.20-times-makespan objective.

The Python entry point independently checks parity coverage and the final
identity map. A native-edge compute/rotate/uncompute fallback covers backend
loading failures or rejected candidates. This fallback preserves semantics but
is not intended to meet the optimization targets without the native backend.

## Files and resources

- `solution.py`: streaming interface, independent semantic guard, and fallback.
- `native_backend.py`: standard-library `ctypes` bindings.
- `phase_compiler.cpp`: C++17 implementation.
- `phase_compiler.so`: bundled Linux x86-64 native backend, requiring POPCNT.

Search uses one thread and an 11.8-second wall-clock budget per workload. Bounded
resynthesis and scheduling follow the search. No numerical rotation angles are
introduced, merged, approximated, or discarded.

To rebuild in the submission directory:

```sh
TMPDIR="$PWD" g++ -O3 -mpopcnt -std=c++17 -fPIC -shared phase_compiler.cpp -o phase_compiler.so
```

## Reproduction

Set `ASSETS` to the supplied participant directory:

```sh
export ASSETS=/path/to/participant
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ASSETS/workspace"
python3 solution.py < "$ASSETS/input/examples.jsonl" > circuits.jsonl
python3 "$ASSETS/workspace/check.py" "$ASSETS/input/examples.jsonl" circuits.jsonl
```

`validate_submission.py` checks all public instances and eight independently
relabeled/reordered variants against the supplied baseline and semantic checker.
Its measurements are recorded in `validation_report.json`. The topology groups
in that report distinguish the lattice-like and chorded public examples; they
are not a claim about unavailable hidden-test labels.

`resource_sanity.py` checks 96-term path, star, and complete-graph inputs, the
fallback's exact semantics, memory usage, and multi-request streaming behavior.
Its measurements are recorded in `resource_report.json`. These additional
uncorrelated stress cases test validity and resource limits, not the correlated
workload cost targets.

## Recorded validation

The recorded public mean cost reduction is **83.05%**, with **82.21%** in the
lower-scoring public topology group. Across all twelve public and relabeled
cases, the mean reduction is **82.70%** and the lower topology-group mean is
**81.87%**. Every circuit passes the supplied exact semantic checker.

The largest observed public/relabeled runtime is **12.81 seconds**. The 96-term
path stress test completes in **13.02 seconds**, and the resource-test process
peaks at **79.86 MiB** resident memory. Streaming checks confirm that responses
are flushed before EOF and that a second workload is served correctly.
