# Protocol and cost model

An instance has `n` vertices 0 through n-1, `edges` (objects with `u`, `v`, `dim`),
and `memory_elements`. The edge's position in `edges` is its ID. Each edge is an
index appearing on exactly its two endpoint tensors. There are no open indices.
An element is one complex number; the memory cap counts elements, not bytes.

A plan is `{"slices": [edge_id, ...], "merges": [[left_id,right_id], ...]}`.
Sliced indices are fixed independently and all assignments are summed. No
cross-slice intermediate caching is used. Slices must be unique valid edge IDs.
There are exactly n-1 merges. Initially live tensor IDs are vertex IDs. Merge
step k consumes two distinct live tensors and creates tensor ID n+k.
Outer products are permitted. The sole final tensor must be a scalar.

After slicing, a tensor's index set is the set of unsliced edges with exactly
one endpoint in that tensor's vertex subset. Merging index sets A and B produces
their symmetric difference. Its arithmetic work is the product of dimensions
in their union, with empty product 1. Thus the work unit is one dense
multiply-accumulate and a scalar product of length D costs D units.

All input tensors for one slice start live. An output tensor is allocated
before its two inputs are freed. Peak memory is the largest sum of sizes of
all live tensors, including that temporary output. Inputs may not be freed
before their final use. Empty-index tensors have size one.

If S is the product of sliced dimensions, total modeled work is
`S * sum(merge_work) + (S - 1)`. The last term sums the slice scalars. One
additional accumulator element is live throughout when S > 1. Unsliced
source tensor backing storage and input I/O are outside this resident-memory
model; sliced inputs are streamed. The model represents independent slice
execution rather than a claim about a particular BLAS kernel's wall time.

To run the baseline or checker from the participant directory:

```
PYTHONPATH=workspace python baseline/solve.py < INSTANCE.json > PLAN.json
python workspace/check_plan.py INSTANCE.json PLAN.json
```

Both scripts use only Python's standard library. The public examples file is a
list of instances; extract an individual object when testing this interface.
