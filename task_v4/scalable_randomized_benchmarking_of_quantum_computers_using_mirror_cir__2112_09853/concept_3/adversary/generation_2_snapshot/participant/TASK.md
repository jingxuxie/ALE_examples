# Native Clifford scrambling: omission-robust construction

Construct one shallow native-geometry Clifford block for each hardware family.
Preserve strong ideal spreading AND spread beyond two sites under CNOT omissions.

## Assets and interface
`input/spec.json` fixes graphs, native budgets, ideal targets, and fault targets.
`input/FORMAT.md` defines exact semantics. `baseline/solve.py` is a weak reference;
`scorer.py` is the complete public exact scorer. No private design is supplied.
The participant tree is read-only. Submit only **artifact.json** in writable OUTPUT.
Example: `python baseline/solve.py --input input/spec.json --output OUTPUT/artifact.json`
Local check: `python scorer.py --input input/spec.json --submission OUTPUT/artifact.json --output OUTPUT/report.json`
Official: `python evaluator/evaluate.py --submission OUTPUT/artifact.json --output OUTPUT/report.json`

## Constraints and scoring
Use listed local words/native CNOTs only, no ancillas; each CNOT round is a matching.
All ideal minimum/mean targets and native round/CNOT budgets remain mandatory.
After ANY set of zero, one, or two distinct CNOT-instance omissions, every one-
and two-site Pauli must have output weight at least THREE, forward AND inverse.
All inputs and omission sets are checked exactly. Faulted circuits have no mean target.
`core_score` is the minimum ideal/robustness attainment ratio, capped at one.
Only static data is evaluated; 2,000,000-byte cap. No solver CPU/time gate applies.
