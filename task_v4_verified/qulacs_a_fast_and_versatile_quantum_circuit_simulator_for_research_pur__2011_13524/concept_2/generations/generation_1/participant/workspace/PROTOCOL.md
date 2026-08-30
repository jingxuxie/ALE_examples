# Circuit witness protocol, version 1

## Input

The command receives two positional paths: an input JSON and an output JSON.
The input has `schema_version`, `conventions`, `tolerances`, and `targets`.
Each target has `id`, `n_qubits`, `connectivity`, `max_cnot`, `max_u3`,
`unitary_real`, and `unitary_imag`. The last two fields are square nested lists
of real numbers; their complex combination is the complete target matrix.
Rows index output basis states and columns index input basis states.

The scored IDs are `unitary_6q` and `unitary_7q`.

Exact gate budgets:
- `unitary_6q`: `n_qubits=6`, `max_cnot=36`, `max_u3=98`.
- `unitary_7q`: `n_qubits=7`, `max_cnot=42`, `max_u3=111`.

The separate demo uses
`demo_2q` and is not included in the scored suite. All matrices are supplied as
double-precision data and are unitary to numerical roundoff.

## Basis and gate order

Qubit zero is the least-significant bit. Basis index
`sum(bit[qubit] * 2**qubit)` represents `|q[n-1] ... q[1] q[0]>`.
The first listed gate acts first: the complete matrix for a list
`[G0, G1, ..., Gk]` is `Gk @ ... @ G1 @ G0`. Empty lists represent identity.
The connectivity entries are undirected edges; either CNOT direction on an
edge is legal. Output wire positions must match the supplied target exactly.

## Output

Write one JSON object mapping every input target ID directly to a gate list.
There is no enclosing `circuits` field. For example, the complete demo answer is:

```json
{"demo_2q": [{"gate": "CNOT", "control": 0, "target": 1}]}
```

A U3 gate has exactly these fields:

```json
{"gate": "U3", "qubit": 0, "theta": 0.2, "phi": -0.3, "lambda": 0.4}
```

Its local matrix is

```text
[[cos(theta/2),                 -exp(i*lambda)*sin(theta/2)],
 [exp(i*phi)*sin(theta/2), exp(i*phi)*exp(i*lambda)*cos(theta/2)]]
```

Angles are arbitrary finite real JSON numbers in radians. They are not
quantized. Booleans, strings, NaN, and infinities are not numbers for this
protocol. A CNOT has exactly `gate`, `control`, and `target`; it flips the
target bit if and only if the control bit is one. Qubit indices must be JSON
integers, not booleans or floating-point values, in `[0, n_qubits)`.

Only the two listed gate types are accepted. Counts are literal list counts:
canceling gates and identity U3 gates still consume budget. Control and target
must be distinct and adjacent. Every target must appear once. Additional IDs,
fields, duplicate JSON keys, or gates are rejected. The complete UTF-8 JSON
output must be a regular, non-symlink file of at most 1 MiB. Write the answer
to the specified path; logging to stdout is allowed but is never evaluated.

## Numerical acceptance

For target `T`, submitted circuit matrix `V`, and `dimension = 2**n_qubits`, set

```text
overlap = trace(T.conj().T @ V) / dimension
infidelity = max(0, 1 - min(1, abs(overlap))**2)
phase = conj(overlap) / abs(overlap) if abs(overlap) > 0 else 1
discrepancy = norm(phase * V - T, "fro") / sqrt(dimension)
```

A target passes exactly when every gate and budget is valid, `infidelity <=
1e-8`, and `discrepancy <= 2e-4`. Both are tested on the whole matrix. For exact
unitaries, squared discrepancy is `2 - 2*abs(overlap)`, so the infidelity
threshold is slightly stricter than the separate discrepancy threshold. The
discrepancy test also checks the aligned matrices directly rather than relying
only on a trace subtraction near one. There is no hidden target accuracy,
preferred topology, or preferred angle representation.

The aggregate `core_score` is passed targets divided by target count. `valid`
means that the output schema and all circuits obey the gate constraints;
`target_met` and `success` require every target to pass. Invalid individual
circuits receive zero for that target. An invalid top-level object receives
zero overall. Approximate valid circuits can have score zero.

## Execution boundary

The submitted directory is read-only during evaluation. Place scratch files in
`/tmp` or beside the specified output file. The runtime exposes the submission,
the public input, an output directory, and standard system libraries, not
other task files. The evaluator runs `solution.py` in a separate isolated
process and reads the resulting JSON; it never imports submission code.
The process has at most 295 seconds, reserving the remainder of the total
300-second budget for checking, and a 4-GiB address-space cap. Address-space
limits apply per process; no aggregate cgroup memory guarantee is claimed.
Execution is pinned to one allowed CPU core and BLAS/OpenMP thread counts
are set to one. NumPy and SciPy are provided; Qulacs is not required.

The evaluator interface is `python evaluator/evaluate.py --submission DIR
--output report.json`. For a static circuit file, use `--witness FILE` instead
of `--submission DIR`. Add `--public` to check only the unscored two-qubit demo.
All scored targets are also public; the flag names the small demonstration,
not a hidden/public split of scientific conditions.
