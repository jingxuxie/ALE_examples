# Native parity-walk synthesis

## Mission
Construct compact, architecture-native CNOT circuits that implement six exact
binary linear maps **and** expose every specified intermediate parity. The
parities represent independently parameterized phase obligations: computing the
final map alone is insufficient.

The fixed suite has 12–20 physical qubits on ladder, grid, and branched graphs.
Both CNOT count and two-qubit depth have hard, per-case budgets. Physical wire
labels are fixed; there are no spare qubits, free permutations, or remote gates.
Feasibility has been checked constructively; no reference circuit is supplied.

## Assets and interface
- `input/instances.json`: all six graphs, target matrices, parity masks, budgets.
- `input/FORMAT.md`: exact algebra, witness schema, depth rule, and limits.
- `baseline/synthesize.py`: dependency-free, semantically correct but deliberately
  inefficient starting point; its output need not meet the budgets.
- `workspace/`: starter assets. Submit **`submission/witness.json`** relative to
  your solution directory, with a circuit for every case. No executable is graded.

From this directory, run
`python3 baseline/synthesize.py --output OUTPUT_DIR/submission/witness.json`,
where `OUTPUT_DIR` is your writable solution directory.
Improve or replace this baseline; the task is circuit design, not package/API
replication. The public instance suite and scoring rules are frozen.

## Fixed bounds and scoring
Submit at most 50,000 CNOTs per case in a UTF-8 JSON file of at most 8 MiB.
`valid` means every circuit obeys the graph, reaches its exact target, and visits
all required parities. `passed` additionally requires both budgets on every case.
`core_score` is the fraction of cases passing both budgets and semantics;
`worst_family_score` is the smallest family pass fraction. `resource_score` is
the mean of each valid case's capped count/depth efficiency, as defined in
`FORMAT.md`; invalid cases contribute zero. All scores lie in [0,1]; one is best.
No timing measurements, floating-point simulation, or reference comparison enter
the score. Synthesis runtime is not scored; the runner's authoring deadline still
applies.

Motivation: Sivarajah et al., *t|ket>: A Retargetable Compiler for NISQ Devices*,
arXiv:2003.10611, Sections 6.3 and 7; Cowtan et al., *Phase Gadget Synthesis for
Shallow Circuits*, arXiv:1906.01734. This is a new finite synthesis benchmark,
not a reproduction of either paper's experiment.
