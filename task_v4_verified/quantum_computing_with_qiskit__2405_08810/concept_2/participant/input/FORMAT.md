# Input and witness format

## Fixed input

`instances.json` is a UTF-8 JSON object with exactly `schema_version` (integer 1),
`suite_id` (`native_cx_linear_v1`) and `targets` (a list). All four listed targets
are scored, with the same data used by the evaluator; there are no hidden target
matrices, extra calibration parameters or hidden resource conditions.

Each target has exactly:

| Field | Meaning |
| --- | --- |
| `name` | Unique circuit key, shown below |
| `family` | `mesh` or `bottleneck`; used for diagnostic family scores |
| `n_qubits` | Number of physical wires, labeled 0 through `n_qubits - 1` |
| `matrix` | Square row-major array of integer 0/1 values, invertible over GF(2) |
| `native_cx` | List of `[control, target, duration]` integer triples |
| `max_cx` | Inclusive native-CX count cap |
| `max_weighted_depth` | Inclusive duration-weighted depth cap in integer ticks |

| Target | Family | Qubits | CX cap | Weighted depth cap |
| --- | --- | ---: | ---: | ---: |
| `mesh_22` | mesh | 22 | 155 | 65 |
| `bridge_26` | bottleneck | 26 | 189 | 66 |
| `mesh_30` | mesh | 30 | 227 | 78 |
| `bridge_34` | bottleneck | 34 | 261 | 79 |

The underlying undirected hardware graphs are connected and irregular, with
degrees two and three. Both directions of each edge are present; their positive
integer durations may differ. A duration belongs to the **ordered** pair, not
merely the undirected edge. Only explicitly listed ordered pairs are native.

## Mathematical convention

Treat the input bits as a column vector indexed in ascending physical wire order:
`output[row] = XOR(matrix[row][column] AND input[column])` over all columns.
Row 0 and column 0 refer to wire 0; no display-string endianness reversal applies.

A gate `[control, target]` updates the target bit by XOR with the control bit,
leaving all other bits unchanged. Gates occur in the submitted list order. To
check exactly, start with the identity matrix and XOR the control **row** into
the target **row** for each gate. The final matrix must equal the supplied matrix,
entry for entry. This proves equality on all basis inputs, and therefore on all
quantum states for these CX-only circuits; sampled input agreement is insufficient.

Every wire carries arbitrary input data. No initialized spare wires, measurement,
reset, phase gates, implicit SWAPs, classical corrections, relabeling, free final
permutations, or approximate equivalence are allowed. A SWAP may be implemented
using native CX gates, but all its gates and duration count.

## Submission

The following is a **schema skeleton, not a solution**:

```json
{
  "schema_version": 1,
  "circuits": {
    "mesh_22": [],
    "bridge_26": [],
    "mesh_30": [],
    "bridge_34": []
  }
}
```

Replace each empty list with a flat ordered list of two-element integer arrays.
All four keys must appear exactly once. Object key order is immaterial; gate
order matters. Only the two top-level keys shown are allowed. No metrics,
matrices, layouts, timing annotations, comments or references may be submitted.

The file must be a regular, nonsymlink, strict UTF-8 JSON file of at most
2,097,152 bytes, with at most 20,000 gate entries per target. This parsing bound is
**not** a scientific count cap: an exact 1,000-gate circuit may be schema-valid
but fail its target's much smaller cap. Empty lists are syntactically permitted
but do not implement these targets.

Duplicate keys (including escaped aliases), unknown/missing fields, booleans,
null, fractional numbers, floating-point syntax such as `1.0` or `1e0`, NaN,
infinities, out-of-range wire indices, self-loops and non-native gates are rejected.
Only JSON integers with absolute value at most `2**63 - 1` are accepted; further
field bounds apply. Integer tokens may have at most 19 magnitude digits. Strings
and keys have at most 128 Unicode characters. The JSON value tree has at most
400,000 values and depth 12 (root depth 1; object keys are not value nodes).
Trailing non-whitespace, a UTF-8 BOM and invalid UTF-8 are rejected.

Any structural or native-gate violation rejects the whole submission. A legal
native circuit with the wrong matrix is instead a valid but incorrect witness.
`workspace/checker.py` is the executable public specification; changing it or
changing public inputs cannot change the evaluator's frozen inputs and rules.
