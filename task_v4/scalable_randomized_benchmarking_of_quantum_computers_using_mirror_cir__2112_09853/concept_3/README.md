# Concept 3, final generation 3: omission-robust Clifford witnesses

Participant entry point: `participant/TASK.md`. Supply only `participant/` to a
fresh solver, with a separate writable OUTPUT directory for `artifact.json`.
The public scorer and reference kernels implement the complete exact contract;
they contain no previous champion, privileged optimizer, or private artifacts.

## Second and final ratchet

All ideal geometry, depth, CNOT, minimum, and mean constraints are unchanged:

| Family | n | Rounds | CNOT cap | Single min | Double min | Single mean | Double mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ladder16 | 16 | 12 | 80 | 8 | 6 | 11.50 | 11.75 |
| grid20 | 20 | 10 | 84 | 9 | 7 | 14.00 | 14.75 |
| bridge18 | 18 | 12 | 90 | 8 | 5 | 12.25 | 13.00 |

Every weight-one and weight-two Pauli must also have output weight at least
THREE in both directions after ANY zero, one, two, or three distinct native
CNOT-instance omissions. Faulted means have no additional target. Occurrence
IDs refer to the original circuit; deletions are simultaneous with no repair.

The evaluator enumerates all `1+m+choose(m,2)+choose(m,3)` scenarios, streaming
one scenario at a time. At the full budgets this is 305,832 scenarios and
890,561,868 input/direction checks across the three families. There is no
sampling or early termination. NumPy is the sole nonstandard dependency.
The broad three-worker sweep took 72.8 seconds with less than 25 MiB RSS per
worker. Official sequential evaluator runtime/RSS are recorded in `status.json`
and `adversary/generation_3/validation.json`; memory remains far below 1 GiB.

## Run from the concept directory

```sh
python -B participant/baseline/solve.py --input participant/input/spec.json --output OUTPUT/artifact.json
python -B participant/scorer.py --input participant/input/spec.json --submission OUTPUT/artifact.json --output OUTPUT/public_report.json
python -B evaluator/evaluate.py --submission OUTPUT/artifact.json --output OUTPUT/report.json
python -B -m unittest discover -s adversary -p 'test_*.py' -v
```

Create writable OUTPUT first. Only static JSON is evaluated. Symlinks,
hardlinks, nonregular files, oversized files, malformed schemas, nonfinite
numbers, and invalid/native-budget-breaking circuits are rejected. The
official evaluator imports only trusted private kernels and its frozen spec,
never participant code. Valid nonpassing artifacts exit zero; invalid artifacts
exit two. Runtime and memory are diagnostic, not solver-time/resource gates.
Native circuit limits remain mandatory and determine `resource_score`.

## Evidence and history

`status.json` is the readiness authority: generation 3, `ratchet_generations: 2`,
and `stop_after_generation: 3`. There will be no fourth generation regardless
of the outcome. No generation-3 fresh agent was launched by this builder.

Generation 1 passed in 544.4 seconds / 43,594 tokens. Generation 2 passed in
1,897 seconds / 142,031 tokens. Their champions and full task snapshots remain
immutable in `champions/generation_1/`, `champions/generation_2/`,
`adversary/generation_1_snapshot/`, and `adversary/generation_2_snapshot/`.
All of `attempts/` also remains untouched.

`adversary/generation_3/champion_triple_sweep.json` records exhaustive actual-G2
champion sweeps, original-instance witnesses, and failure clusters. All ideal
and up-to-two-omission targets still pass. Triple omissions produce 321, 282,
and 363 failing scenarios for ladder16, grid20, and bridge18 respectively;
every failure is genuinely third-order, with all proper omission subsets
passing. Each family's worst output weight is one, giving new core score 1/3.
This is an added fault-tolerance order, not a numerical threshold squeeze.

Validation includes dense unitary checks, independent scalar propagation of
explicitly deleted small and actual circuits, count-four rejection, complete
public/official baseline parity, source/seed hashes, and independent failure
witness checks. The weak baseline's exact score and resources are public in
`participant/input/baseline_scores.json`, using only public artifact paths.

Generation-3 solvability is **unknown / hard_open**: no complete passing G3
witness is known. Prior-generation successes do not establish G3 feasibility.
Scientific assumptions and limitations are in `participant/input/FORMAT.md`;
no global Omega mixing or general physical-noise theorem is claimed.
