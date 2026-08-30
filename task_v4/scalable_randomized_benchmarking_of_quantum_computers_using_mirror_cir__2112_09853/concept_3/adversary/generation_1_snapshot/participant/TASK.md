# Native Clifford scrambling: witness construction

Construct one shallow native-geometry Clifford block for each hardware family.
Every one- and two-site Pauli must spread in BOTH forward and inverse directions.
This is a circuit-design task motivated by error spreading in mirror benchmarking.

## Assets and interface
`input/spec.json` fixes the graphs, budgets, and targets; `input/FORMAT.md` is the
exact gate/schema/scoring contract. `baseline/solve.py` is a runnable reference.
The participant tree is read-only. Write the static JSON file **artifact.json**
inside the supplied writable OUTPUT directory; do not submit executable code.
Example: `python baseline/solve.py --input input/spec.json --output OUTPUT/artifact.json`
Organizer: `python evaluator/evaluate.py --submission OUTPUT/artifact.json --output OUTPUT/report.json`

## Constraints and scoring
Use only listed local Clifford words and native directed CNOTs; no ancillas.
Each CNOT round is a matching. Round/CNOT budgets and the 2,000,000-byte cap are hard.
All `3n` single-site and `9*n*(n-1)/2` two-site Paulis are checked exactly, both ways.
Every family's separate minimum/mean targets must pass; averages cannot hide failures.
`core_score` is the minimum target-attainment ratio, capped at one. Only data is evaluated.
Single-CNOT deletion is diagnostic only. No global-mixing or full MRB theorem is certified.
