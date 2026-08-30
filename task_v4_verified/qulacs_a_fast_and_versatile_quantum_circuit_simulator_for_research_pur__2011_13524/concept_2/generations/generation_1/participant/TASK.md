# Compact circuits for public unitary operators

## Mission

Recover a compact circuit for each complete operator in `input/targets.json`.
Use arbitrary one-qubit U3 rotations and nearest-neighbor CNOTs on the supplied
line connectivity, in either CNOT direction. No ancillas, measurements, other
gates, or qubit relabeling are allowed.

- `unitary_6q`: 6 qubits, at most **36 CNOTs** and **98 U3 gates**.
- `unitary_7q`: 7 qubits, at most **42 CNOTs** and **111 U3 gates**.

Match the **entire unitary**, not its action on one initial state. Global phase
is irrelevant. Every target requires operator infidelity at most `1e-8` and
phase-aligned normalized Frobenius discrepancy at most `2e-4`. All operator
entries, connectivity, gate budgets, and numerical conditions are public.
Any legal equivalent circuit is accepted.

## Assets and interface

- `input/targets.json`: scored operators and exact constraints.
- `input/demo.json` and `input/demo_witness.json`: unscored two-qubit example.
- `workspace/PROTOCOL.md`: complete gate, matrix, JSON, and scoring conventions.
- `workspace/check.py`: public full-operator checker, taking input and witness paths.
- `baseline/solution.py`: runnable identity baseline.

Submit a directory containing `solution.py` and any supporting files. It runs
as `python solution.py INPUT_JSON OUTPUT_JSON`. Write a JSON object mapping
every input target ID to its ordered gate list at `OUTPUT_JSON`; stdout is not
the answer. The baseline uses the same interface:
`python baseline/solution.py input/targets.json answer.json`.

## Objective and resources

The score is the fraction of targets whose circuits are legal and meet both
error thresholds. The objective is **1.0, passing both targets**; approximation
errors are diagnostic only. Use any construction strategy.

Development time is one hour. Evaluation has a 300-second wall limit and 4-GiB
memory limit, on one CPU thread with Python, NumPy, and SciPy available, without
network or accelerator access. Supporting precomputed artifacts are permitted.
