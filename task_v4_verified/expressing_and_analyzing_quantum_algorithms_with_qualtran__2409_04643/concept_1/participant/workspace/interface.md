# Interface

`input/workloads.json` contains a `cases` list. A case has `id`, `family`,
`nodes`, and `edges`. Nodes are numbered by their array position. Each node has
integer `duration` and `workspace`. Edges are `[source, destination, width]`;
each represents a distinct live quantum register. Parallel edges are allowed.
The graphs are acyclic. Indices are labels, not an execution order.

A node with no incoming edges is an allocation/preparation. A node with no
outgoing edges is a final consume/reset. Other nodes are indivisible composite
bloqs. These are abstract resource contracts, not claimed decompositions of a
particular chemistry Hamiltonian. Port data must follow the supplied graph;
no recomputation, fusion, cancellation, extra serialization constraints or
parallel execution is permitted. Allocation and final consumption are explicit.

Immediately before a node runs, all its incoming registers must be live. Remove
them from the live set. Its instantaneous footprint during the operation is

`remaining_live_width + max(total_input_width, total_output_width) + workspace`.

The operation's contribution to qubit-time is `duration * footprint`. After it
runs, add all outgoing registers to the live set. Peak qubits is the maximum of
all during-operation footprints and all between-operation live widths, including
the initially empty boundary. Qubit-time is the sum of operation contributions.
All arithmetic is exact integer arithmetic. Every case ends with no live edges.

The artifact is `{"schedules": {"case_id": [node_index, ...], ...}}`.
Each schedule must be a permutation containing every node exactly once and
respect every edge. All cases are required; additional case IDs are rejected.
Booleans, floats, duplicate keys and nonfinite numbers are not valid integers.

For a case, define `cost = peak**0.7 * qubit_time**0.3`. The per-case improvement
is `baseline_cost / submitted_cost`. Core score is the geometric mean of all
per-case improvements. Worst-family score is the minimum of the corresponding
within-family geometric means. The baseline is the immutable evaluator copy of
the supplied current-champion schedules. The runnable baseline emits these
precomputed plans. Core improvement must be at least 1.06 and each individual
case's improvement at least 1.02. In addition to these score targets, each case
must have `submitted_peak <= 1.05 * baseline_peak`. Invalid schedules score zero.

Run the baseline with:

```
python3 baseline/solve.py --input input --output /YOUR_OUTPUT/schedules.json
```

Run the public diagnostic with:

```
python3 workspace/check.py --input input --submission /YOUR_OUTPUT
```

The public checker uses exactly the disclosed scoring model. The private checker
has an independently implemented liveness simulation and additional malformed
artifact tests. Neither requires an optimal schedule. NumPy and SciPy are
available, but the baseline and checker need only Python's standard library.
