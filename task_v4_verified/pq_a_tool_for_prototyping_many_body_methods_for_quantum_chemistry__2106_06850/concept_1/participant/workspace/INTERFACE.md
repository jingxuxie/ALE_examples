# Contract version 1

An input object has `dimensions` (positive occupied/virtual sizes), `tensors` (names to ordered orbital-space lists), `index_types`, `terms`, and `memory_cap`. A term is `{ "inputs": [[tensor_name, axis_string], ...], "output": axis_string }`. Each is an ordinary dense Einstein contraction with a separate output. The tensor names are meaningful only within the instance. No tensor symmetry, antisymmetry, factorization or zero value may be assumed. Each term has three to six factors, unique axes within each factor, and at most two occurrences of any index. The source families are CCSDT right residuals, CCSD left/density kernels, EOM-CCSD response, and CCSDTQ residuals. Batch sizes are 20–80; occupied dimensions 4–20, virtual dimensions 12–112. The supplied space information, not English tensor names, defines shapes.

Output is `{ "steps": [...] }`. Exactly three step forms are accepted:

* `{ "id": "new_name", "inputs": [[name, axes], [name, axes]], "output": axes }`: allocate and evaluate a binary dense einsum. Every omitted index is summed. Operand axes bind, in order, the existing tensor's axes to local labels, so a reused tensor can be renamed. A contraction may be an outer product. Repeated axes within an operand are not supported. Names cannot be reused after deletion.
* `{ "emit": term_number, "input": [name, axes], "output": axes }`: supply that term's result. The `output` ordering is a zero-cost view of the operand and must preserve all its indices. Each requested term must be emitted exactly once. This does not delete the operand.
* `{ "delete": "temporary_name" }`: free a live temporary. Input tensors cannot be deleted.

Input tensors are permanently resident and excluded from scratch. Emitted final arrays are excluded from scratch; emitting copies/views into that external output store, whose data cannot be used as operands later. All explicitly created temporaries, including result temporaries, count until deleted. A new temporary must be allocated before its operands can be freed. The cap is measured in scalar elements. No spilling or slicing is represented by this interface.

Arithmetic cost for each binary step is the product of dimensions of its distinct input indices, multiplied by two if any input index is summed, otherwise by one. Renaming, output copies, and deletions have zero arithmetic cost. The objective measures this explicit hardware-independent dense arithmetic model, not actual einsum runtime. All retained intermediates obey the declared memory cap; runtime is charged to the planner itself.

Correctness is checked exactly as a tensor-network monomial under dummy-index renaming and commutation of scalar factors. Input tensors are not numerically sampled to decide correctness. This permits reuse of equivalent subnetworks with different dummy labels and output-axis orders but does not permit changing the requested mathematical outputs. The interface has no addition node or symmetry rewriting. Plans exceeding 30,000 steps are invalid.

Local use:

```
python baseline/solve.py input/right_triples.json /tmp/plan.json
python workspace/contract.py input/right_triples.json /tmp/plan.json
```

The supplied baseline performs exact per-term flop/peak-memory Pareto planning, with no cross-term reuse. Its cost is recomputed on every hidden case before comparison. All hidden objectives and resource limits are the thresholds stated in TASK.md; there is no additional accuracy requirement or private optimizer-specific format.
