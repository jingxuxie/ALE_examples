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

The 62 policies returned by `router.settings()` are fixed and public:

- Original 18: 16 weighted settings with horizons 2/4/8/16, factors 0.5/0.9,
  ascending/seeded ties; two horizon-8 lexicographic settings with ascending/descending ties.
- Six long-horizon weighted settings: `(horizon,factor)` is `(64,0.97)`,
  `(200,0.97)`, or `(200,1.0)`, each with ascending/seeded ties.
- The retained suffix-embedding policy examines cuts `(0,4,8,12,16,24)` below the gate count.
- 36 future-emphasis weighted settings: horizons `(4,8,16,32,64,200)` crossed
  with factors `(1.1,1.5,2.0)` and ties `(ascending,seeded)`.
- One all-program suffix-embedding policy examines `range(0,len(gates),4)`.

The source field `decay` is the geometric factor. Values above one emphasize
more distant future layers; they are not decaying weights. Seeded edge ordering
uses Python `random.Random(1729)`. The six relabelings are exactly
`router.relabelings(16)`: identity, physical-11, physical-29, logical-47,
joint-71, and joint-103. All 62 policies run in each family, for 372 portfolio
routes per valid witness. The minimum-cost policy wins independently in each family.

A relabeling consistently changes hardware edges, logical demands, initial
placement, reference operations, and final placement. It never grants optimized
initial placement. Every reference and every portfolio route is independently replayed.

### Public embedding bounds

Both embedding policies use the same helpers and pay for all physical transitions.
The prefix and incumbent routes use weighted horizon 16, factor 0.9, ascending ties.
Each suffix embedding search uses a 12,000-visit budget: a call increments its
counter and returns immediately if that counter exceeds the budget. It also stops
after 16 complete embeddings; it orders the found embeddings by total initial-to-target
hop distance and returns at most four. The source specifies deterministic degree,
already-mapped-neighbor, displacement, and node-ID ordering.

Each mapping transition obtains a legal spanning-tree token plan and then runs a
bounded token search of at most 2,500 expanded states, using priority
`cost+0.75*sumHopDistances`. Tree roots are the distinct values among node 0,
node 15, and the lowest-ID maximum-degree node. The exact tree construction,
leaf ordering, candidate edges, and token-search branch bounds are in `embedding.py`.
These are fixed computational limits, not hidden data or submitted costs.

Only the new all-program policy adds two safe cuts: skip a boundary if its prefix
SWAP count already meets/exceeds the incumbent; skip a mapping if
`prefix_swaps+ceil(sumHopDistances/2)` meets/exceeds the incumbent. One SWAP can
reduce the total token distance by at most two, so neither cut removes an improving
route. The old suffix policy, its boundaries, and its bounds remain unchanged.

### Scores

Let `W` be reference SWAPs, `P` a family's minimum portfolio SWAPs, and `G` the
demand count. Define `R=P/W`, `N=(G+3*P)/(G+3*W)`, and `D=P-W`.
Its score is `max(0,min(1,(R-1)/1.5,(N-1)/0.35,D/16))`.
`core_score` is the mean family score. `worst_family_score` and `resource_score`
are the minimum. `valid` means all format, regularity, and route checks passed.
`passed` additionally requires `R>=2.5`, `N>=1.35`, and `D>=16` in every family.
Invalid submissions have zero scores. The checker reports counts, ratios, and
the winning setting; it never accepts a claimed cost.

Evaluator CLI: `python -I -B evaluator/evaluate.py --solution-dir SOLUTION_DIR`.
Optional `--output-dir DIR` also writes `DIR/result.json`.
Python API: `evaluate(solution_dir, output_dir=None) -> dict`.
