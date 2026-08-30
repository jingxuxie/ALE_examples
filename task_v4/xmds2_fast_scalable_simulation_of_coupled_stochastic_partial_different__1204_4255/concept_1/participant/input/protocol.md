# Protocol

An instance has `dimensions` (3--6), `sizes` (2--4 positive field sizes, each 1--4), `capacity` (scratch units, always at least the largest field), `axis_cost`, `transpose_cost`, and `requests` (30--100 ordered reads). Costs are positive integers supplied in each instance. No family name or baseline cost is provided at evaluation time.

A representation is `(field, mask, layout)`. Bit `axis` of `mask` selects real (0) or spectral (1) basis in that dimension; `layout` is the distributed dimension, from 0 through `dimensions-1`. Every field starts with an immutable current-version home representation `(field, 0, 0)`. Homes are pinned, reside outside the scratch budget, and cannot be dropped or overwritten. All other representations occupy `sizes[field]` scratch units. Only one copy of a representation is permitted.

Each request is `{"field": integer, "mask": integer, "layout": integer, "updates": [field,...]}`. Reads must be served in order. Immediately after a read, each listed field receives a new home value and ALL its nonhome cached representations disappear. Unlisted fields are unchanged. Read/update execution itself is outside the transform-cost objective. No value from a future version exists before its update.

Return `{"actions": [...]}` with at most 100,000 actions. An action is one of:

* `["axis", field, source_mask, source_layout, axis, keep]`: source must exist; `axis != source_layout`. Toggle that mask bit in the same layout. Charge `sizes[field] * axis_cost[source_layout][axis][old_bit]`. `keep` is a JSON boolean. With `true`, retain the source and allocate the destination. With `false`, reuse the source buffer (source cannot be home). Destination must not already exist. Transforming into home is prohibited. In-place and out-of-place costs are equal in this explicitly idealized model.
* `["transpose", field, mask, source_layout, destination_layout, keep]`: preserve basis and change layout, with unequal layouts. Charge `sizes[field] * transpose_cost[source_layout][destination_layout]`. The same source, destination, and `keep` rules apply.
* `["drop", field, mask, layout]`: discard an existing nonhome representation, for zero cost.
* `["read"]`: the representation of the next request must exist. Advance the trace and apply its updates.

Memory is checked after EVERY action; in-place reuse does not temporarily require a second buffer. Actions before, between, and after reads are permitted; their costs always count. After the last action all requests must have been read. Numerical transforms are not submitted: the checker verifies the representation and version semantics exactly.

Workload families emphasize shared intermediate bases, distributed-layout changes, unequal field sizes, field-version invalidations, and mixed anisotropic transforms. All full traces and costs are visible to the planner. Private instances vary order, costs, working sets, and update locations within these rules; the objective is general planning, not identifying a family.

For each valid instance, let `ratio = submitted_cost / baseline_cost`. `core_score = 1 - exp(mean(log(ratio)))`; family scores use the same formula, and `worst_family_score` is their minimum. Passing requires all plans valid, `core_score >= 0.20`, `worst_family_score >= 0.08`, and resource compliance. The frozen baseline is exactly `baseline/solve.py`. A zero-cost legitimate instance, if supplied, uses ratio 1 when both costs are zero; the supplied distribution has positive costs.

Use `/usr/bin/python3` (Python 3.10, NumPy 1.21, SciPy 1.8 are available). At evaluation `PYTHONPATH` includes `/task/workspace` and `/submission`; relative paths should be based on `__file__`, not the launch directory. Standard input/output are the only instance channel; diagnostics belong on stderr. No evaluator or hidden files are mounted. A public check is `python3 workspace/smoke.py path/to/solve.py`.
