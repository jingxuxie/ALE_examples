# Compact circuits for public unitary operators

Recover a compact circuit for each complete target operator in
`input/targets.json`. The targets act on four and five qubits. You may use
arbitrary one-qubit U3 rotations and nearest-neighbor CNOT gates on the supplied
line connectivity, with either CNOT direction. The four-qubit circuit may use
at most **12 CNOTs** and the five-qubit circuit at most **20 CNOTs**. Each circuit
may use at most **80 U3 gates**. No ancillas, measurements, other gates, or qubit
relabeling are allowed.

The objective is equivalence of the **entire unitary**, not state preparation
for a particular input. Global phase is irrelevant. Both operator infidelity
at most `1e-8` and phase-aligned normalized Frobenius discrepancy at most `2e-4`
are required. All target entries, connectivity, budgets, and acceptance
thresholds are public; the target operator, not a particular decomposition,
defines the answer.

## Assets and interface

- `input/targets.json`: both scored operators and their constraints.
- `input/demo.json` and `input/demo_witness.json`: an unscored two-qubit format
  and ordering example.
- `workspace/PROTOCOL.md`: complete matrix, JSON, gate, and scoring conventions.
- `workspace/check.py`: public full-operator checker; run with input and witness paths.
- `baseline/solution.py`: a runnable, deliberately weak identity baseline.

Submit a directory containing `solution.py` and any supporting files. It runs as
`python solution.py INPUT_JSON OUTPUT_JSON`. Write a JSON object mapping every
target ID to its ordered gate list at `OUTPUT_JSON`. Standard output is not the
answer. The baseline uses the same interface:
`python baseline/solution.py input/targets.json answer.json`.

## Resources and scores

Development time is one hour. Evaluation, including executing the submitted
program, has a 300-second wall limit and a 4-GiB memory limit. Runtime uses a
single CPU thread, with Python, NumPy, and SciPy available and no network or
accelerator. Supporting precomputed artifacts may be included in the submission.

Each scored target earns one point only when its circuit is legal and meets
both error thresholds. The reported score is the fraction of targets passed;
the objective is **1.0, passing both targets**. Approximation errors are also
reported as diagnostics. Use any construction strategy.
