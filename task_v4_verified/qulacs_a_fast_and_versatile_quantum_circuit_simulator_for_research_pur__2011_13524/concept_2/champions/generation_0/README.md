# Compact full-operator circuits

Run the submission using:

```sh
python solution.py INPUT_JSON OUTPUT_JSON
```

`solution.py` reads the requested target IDs and emits their ordered gate lists
from `circuits.json`. All circuit data are bundled; runtime needs only Python's
standard library and does not optimize, compile code, use the network, or write
into the submission directory. The supplied two-qubit demo is supported too.

The circuits were synthesized locally from the public target matrices using
analytic-gradient optimization with a nearest-neighbor CNOT-topology search.
They implement the complete operators, with the supplied little-endian qubit
ordering and first-listed-first-applied gate convention, up to global phase.

## Public full-operator validation

| Target | CNOT gates | U3 gates | Operator infidelity | Normalized Frobenius discrepancy |
|---|---:|---:|---:|---:|
| `unitary_4q` | 12 | 28 | 7.66e-14 | 2.76e-7 |
| `unitary_5q` | 20 | 45 | 3.80e-13 | 6.17e-7 |

Both circuits pass all gate, connectivity, budget, and accuracy checks. The
public checker's report is included as `validation.json`.
