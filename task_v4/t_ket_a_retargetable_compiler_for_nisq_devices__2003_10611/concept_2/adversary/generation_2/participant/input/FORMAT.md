# Witness and checker interface

Run `python -B input/benchmark.py /path/to/output/witness.json` from the participant
folder. The participant tree is read-only; create files only in your output directory.
The evaluator reads `SOLUTION_DIR/witness.json` and executes no submission code.
The entire UTF-8 JSON file must be a regular non-symlink file of at most 1,000,000
bytes. Duplicate keys, nonfinite numbers, booleans used as integers, additional
fields, and unrecognized operations are invalid.

The exact top-level keys are:

```json
{
  "version": 1,
  "hardware": "ring16",
  "gates": [[0, 2], [2, 3]],
  "route": [["swap", 0, 1], ["gate", 0, 1, 2], ["gate", 1, 2, 3]],
  "final_mapping": [1, 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
}
```

This small illustration explains syntax only; it fails the size/coverage constraints.

## Circuit

- Hardware is `ring16`, `ladder16`, or `grid16`, as defined by `router.hardware`.
  These connected graphs have respectively 16, 22, and 24 undirected edges.
  Ladder rungs are `(node,node+8)` for `node=0..7`; the grid is row-major 4 by 4.
- All 16 logical wires and all physical nodes are numbered 0 through 15.
  Logical wire `qubit` initially occupies physical node `qubit`. There are no ancillas.
- `gates` is a list of 48 through 200 ordered pairs `[control,target]` with distinct
  operands. Gate ID is its zero-based position. It denotes a required CX demand;
  either orientation is native on each hardware edge.
- For each wire, incident gate IDs must execute in increasing order. Disjoint gates
  may commute. This is a routing-only problem: elimination, algebraic resynthesis,
  gate reversal, bridges, or extra unlisted logical operations are not allowed.
- Every wire occurs in at least four gates, at most `min(40,ceil(4*gate_count/16))`
  gates, and interacts with at least two distinct wires. The undirected interaction
  graph is connected and has at least 16 distinct edges. A pair occurs at most eight
  times. A pair may not recur as the immediately next gate on **both** its wires,
  even when disjoint gates intervene. These rules exclude simple idle-wire,
  concentration, and cancellation padding.

## Route certificate

- `["swap",physical_a,physical_b]` swaps the occupants of adjacent distinct nodes.
- `["gate",gate_id,physical_control,physical_target]` executes that exact demand.
  Both physical endpoints must match the current placement, in the correct order,
  and be adjacent. Every predecessor on each of its two wires must have executed.
- Execute every gate exactly once. The route has at most 20,000 operations and
  between 8 and 200 SWAPs. The lower SWAP limit avoids a near-zero denominator.
- `final_mapping[logical_wire]` gives its physical node after the entire route.
  It must exactly match replay. Output permutation is allowed for **both** methods;
  neither method pays for restoration. There is no free initial remapping.

## Robustness, costs, and scores

All families in `router.relabelings(16)` are public and fixed. A relabeling changes
the hardware edges, logical gate operands, initial placement, reference route, and
final placement consistently. It never grants a fresh optimized placement. Every
reference and trusted portfolio route is independently replayed in every family.
The portfolio contains 16 weighted settings (horizons 2/4/8/16, distance decays
0.5/0.9, ascending/seeded ties) and two lexicographic horizon-8 settings with
ascending/descending ties. Six additional weighted settings use horizons/decays
`(64,0.97)`, `(200,0.97)`, and `(200,1.0)`, each with ascending and seeded ties.
The final setting uses the supplied bounded suffix-embedding policy with explicitly
paid native token routing. All 25 settings run; the cheapest wins for that family.

Let `W` be reference SWAPs, `P` that family's minimum portfolio SWAPs, and `G` the
demand count. Define `R=P/W`, `N=(G+3*P)/(G+3*W)`, and `D=P-W`.
The family's score is
`max(0,min(1,(R-1)/1.5,(N-1)/0.35,D/16))`.
`core_score` is the mean family score; `worst_family_score` and `resource_score` are
the minimum. `valid` means all format, circuit, and replay checks passed.
`passed` additionally requires `R>=2.5`, `N>=1.35`, and `D>=16` in every family.
`reason`, full per-setting counts, and per-family ratios are reported. Invalid
submissions have zero scores. Costs are computed, never accepted from the witness.

Evaluator CLI: `python -I evaluator/evaluate.py --solution-dir SOLUTION_DIR`.
Optional `--output-dir DIR` also writes `DIR/result.json`.
Python API: `evaluate(solution_dir, output_dir=None) -> dict`.
