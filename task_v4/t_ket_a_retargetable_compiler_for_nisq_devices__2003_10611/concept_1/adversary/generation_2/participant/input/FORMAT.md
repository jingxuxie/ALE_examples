# Input and output contract

Input is a JSON object with fields:

- `id`: an instance identifier, not a hidden label.
- `family`: `chain`, `ring`, `grid`, `ladder`, `tree`, or `modular`.
- `n`: the number of physical and logical wires, between 12 and 28.
- `edges`: undirected `[physical_a, physical_b, positive_weight]` triples forming a connected graph. Calibrated weights are between 0.45 and 2.8.
- `initial`: a permutation; `initial[logical]` is its initial physical location. This placement is fixed.
- `gates`: 96–240 ordered `[logical_a, logical_b]` pairs of distinct wires. Each indexed gate is an opaque operation, not an algebraic expression available for cancellation or resynthesis. Preserve its operand orientation. Gates on disjoint logical wires may be reordered; every wire must retain its original gate order.

Output is `{"operations": [...]}`. An operation is either `["gate", gate_index]` or `["swap", physical_a, physical_b]`. Each gate executes on its logical operands' current physical locations. Every operation must use an architecture edge; every indexed input gate must execute exactly once. SWAPs update the placement. The final placement is unrestricted. At most 30,000 output operations are allowed. Malformed or non-finite output is invalid.

A gate adds its edge weight to calibrated work; a SWAP adds three times its edge weight. Starting with zero depth on every physical wire, an operation starts after both wires' preceding operations and advances both ending depths by one for a gate or three for a SWAP. Let `depth` be the maximum final wire depth. **Cost = calibrated work + 0.05 * depth.**

For valid candidate/reference cost ratios `ratio`, quality is `1 - exp(mean(log(ratio)))`. Compute it across the suite and separately within every family. Overall quality must be at least 0.40 and every family at least 0.30, with all routes valid and resources within the limits in `TASK.md`. An invalid case does not disappear from the average.
