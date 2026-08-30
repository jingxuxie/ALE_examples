# Interface and exact semantics

Input is one JSON object per line: `{"n":16,"edges":[[0,1,3,2],...],"terms":[3,7,...]}`. Each directed edge is `[control,target,error_weight,duration]`; weights are positive integers and durations are integer clock ticks. Both directions exist, but their properties may differ. The underlying graph is connected. Qubit indices are `0..n-1`; `12 <= n <= 28`; there are 24–96 distinct nonzero term masks; native error weights are 1–12 and durations 1–6.

Term index `j` represents the rotation `exp(-i theta_j Z(mask_j)/2)`, with an independent arbitrary real symbol `theta_j`. Bit `q` in a mask refers to qubit `q` (little-endian convention). There are no ancillas or free input/output permutations.

Output: `{"ops":[["cx",control,target],["rz",qubit,term_index],...]}`. Only native directed CX edges are allowed. Each RZ has zero resource cost and must occur exactly once for its term index. At that operation the current Boolean row on its qubit must equal the requested mask. Starting rows are `1 << q`; CX replaces `row[target]` with `row[target] XOR row[control]`. Final rows must again be identity. These conditions certify the full symbolic unitary, not just computational-basis probabilities. No measurements, reset, duplicate rotations, output relabeling, or other gate types are permitted.

Every CX incurs its edge's error weight. Its start time is the maximum ready time of its two qubits, and both become ready after the edge duration. RZ does not advance time. The makespan is the largest final ready time. The scalar cost is `sum(error_weight) + 0.20 * makespan`. This is a declared calibrated execution-cost surrogate, not a claim of an exact physical fidelity model.

Each case reduction is `1 - submitted_cost / baseline_cost`; scores are arithmetic means, with equal numbers of cases per family. Passing requires every circuit valid, every case within 15 seconds, mean reduction >= 0.40, and every family mean >= 0.25. A slower or invalid response fails the task irrespective of other scores. All numeric indices must be JSON integers, not booleans. Responses larger than 16 MiB or more than 100,000 operations are invalid.

Run locally, for example: `PYTHONPATH=workspace python3 baseline/solution.py < input/examples.jsonl`. Public checker: `python3 workspace/check.py input/examples.jsonl circuits.jsonl`. Evaluation mounts these assets at `/task` and submission files at `/submission`; working directory is `/submission`, and `/task/workspace` is on `PYTHONPATH`. During development, use the real paths supplied by the runner instead.
