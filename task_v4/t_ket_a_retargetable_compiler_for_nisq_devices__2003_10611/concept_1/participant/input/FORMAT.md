# Routing contract

Input fields:

- `id`: instance name; not a source of hidden labels.
- `family`: `chain`, `ring`, `grid`, `ladder`, `tree`, or `modular`.
- `n`: number of physical and logical qubits, between 12 and 28 inclusive.
- `edges`: undirected `[physical_a, physical_b, positive_weight]` triples. Weights lie between 0.45 and 2.8. The architecture is connected.
- `initial`: a permutation; `initial[logical]` is its starting physical location. This placement is fixed, not free.
- `gates`: 96–240 ordered `[logical_a, logical_b]` pairs of distinct wires. These are opaque, noncommuting, two-qubit operations. Their pair orientation must be preserved. There are no cancellations or identities to exploit. Gates on disjoint logical wires may be reordered.

Output is `{"operations": [...]}`. Each operation is either `["gate", gate_index]`, referring to the indexed original gate, or `["swap", physical_a, physical_b]`. No other operation type is allowed. A gate executes on the current positions of its two logical operands. Gates and SWAPs must use an architecture edge. Every original gate must execute exactly once, after all earlier gates sharing either logical wire. The final logical-to-physical permutation is unrestricted; the validator tracks it exactly.

For each gate add the edge weight to calibrated work. For each SWAP add three times the edge weight. Starting with every physical wire at depth zero, an operation starts after both wires' previous operations and advances both wire depths by one for a gate or three for a SWAP. Let `depth` be the maximum ending wire depth. Total cost is `calibrated_work + 0.05 * depth`.

For valid case costs `candidate` and fixed baseline costs `baseline`, quality is `1 - exp(mean(log(candidate / baseline)))`. The suite core is the quality across all cases; worst-family score is the minimum of the same quality computed separately for each of the six architecture families. All routes must be valid, core must be at least 0.15, worst-family score at least 0.08, and all resource limits must hold. A failed case invalidates the submission rather than disappearing from an average. More than 30,000 output operations or non-finite numbers are invalid.

Public examples use the same size ranges, calibration variation, and workload mechanisms as hidden cases. Workloads include matching layers, persistent interaction patterns with changing labels, hub traffic, dense pair coverage, and varying locality. Hidden seeds are held out. There are six cases per family. The supplied baseline runs four deterministic lookahead/decay configurations and selects the lowest-cost legal route.

Public check: `python3 workspace/check.py INSTANCE.json ROUTE.json`. Baseline: `python3 baseline/solve.py < INSTANCE.json > ROUTE.json`.
