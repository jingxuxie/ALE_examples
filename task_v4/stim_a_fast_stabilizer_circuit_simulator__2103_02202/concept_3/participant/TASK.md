# Exact Clifford synthesis on a grid

Realize the signed Clifford target in `input/target.json` on the 36-qubit grid in `input/constraints.json`, using only H, S, and neighboring CX, with no extra qubits. Meet every published CX-count, entangling-depth, and total-gate bound. Global phase is ignored; generator signs are not.

Write `OUTPUT_DIRECTORY/circuit.json` at the top level of the writable output directory supplied in your prompt, following `input/circuit.schema.json` and `input/FORMAT.md`. Participant assets are read-only. Ordered layers contain qubit-disjoint gates. Entangling depth counts layers containing CX. Maximum artifact size is 64 MiB. Submitted code is never executed by the evaluator.

`baseline/circuit.json` is exact and topology-valid but exceeds the budgets; `workspace/circuit.json` is the same read-only starting artifact. `python3 baseline/solve.py --output OUTPUT_DIRECTORY` copies the baseline to the output directory (`--output` defaults to the current directory). Preview with `python3 input/check_circuit.py OUTPUT_DIRECTORY/circuit.json`.

Acceptance requires all 72 signed generator images and all resource bounds. For exact native circuits, score is 100 times the minimum of 1 and the three budget/usage ratios; otherwise it is zero. Trusted evaluation has limits of 10 CPU seconds, 15 wall seconds, and 512 MiB memory.
