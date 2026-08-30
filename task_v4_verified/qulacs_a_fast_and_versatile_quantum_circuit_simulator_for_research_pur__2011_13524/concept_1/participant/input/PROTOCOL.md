# Interface

Input is `{"cases":[CASE,...]}`. Each case has `id`, `n_qubits`, `gates`,
`max_block_qubits`, `max_block_operations`, `repetitions`, and `hardware`.
Gates have `qubits` (distinct indices), `kind` (`dense`, `diagonal`, or
`permutation`), and `epoch`. Their list indices identify operations.
These are opaque unitary kernels: arbitrary gates sharing a qubit retain their
source order. Disjoint gates may commute. Epochs are separated by nonunitary
barriers and must remain strictly ordered; no block crosses an epoch.

Output is `{"schedules":{"CASE_ID":[[gate_index,...],...]}}`.
Each inner list is an ordered fused block. Every gate appears exactly once.
The flattened list preserves the per-qubit source order and epoch order.
Each block observes both size caps. You need not return dense gate matrices.
These ordering constraints are a sufficient, directly checkable certificate of
equivalence for every possible numerical choice of the opaque gate kernels.

Bounds: 8–28 qubits, 120–1500 operations, 1–4 epochs, gates on 1–3 qubits,
block support cap 3–6, operation cap 8–48, repetitions 1–128. Hidden evaluation
contains 25 cases (five families with five cases each). IDs do not carry structure
information. All numeric hardware coefficients are supplied in each case.

# Cost

All units are normalized modeled resource units. For a block let `width` be its
distinct qubit count and `count` its operation count. Its specialization is
`diagonal` if all gates are diagonal, `permutation` if all are permutation, and
`dense` otherwise. A singleton retains its original specialization.

Per state-vector application:

```
arithmetic = 2**width  if dense else 1
stride = 1 + stride_penalty * max(0, min(block_qubits) - cache_qubits)
update = launch + max(memory * stride, arithmetic * compute)
```

Construction (zero for singleton):

```
entry_count = 4**width if dense else 2**width
construction = build * (count-1) * entry_count
```

Block cost is `repetitions * update + construction`. Total cost is the sum.
The objective is the geometric mean of `baseline_cost / submitted_cost` across
all hidden cases; each family is measured with its own geometric mean. Validity
and resource limits are mandatory, independently of speedup. NaN, infinities,
duplicate/missing indices, booleans as integers, and out-of-order dependencies
are rejected. The full published implementation is in `workspace/model.py`.

# Public run

```
python3 baseline/solution.py input/examples.json /tmp/plans.json
python3 workspace/check.py input/examples.json /tmp/plans.json
```

During a read-only fresh run, replace `/tmp/plans.json` with a file inside the
designated output directory. Include needed helpers in your submission;
evaluation does not rely on the participant workspace remaining writable.
