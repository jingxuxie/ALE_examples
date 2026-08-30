# Compact unitary circuits

Run:

```sh
python solution.py INPUT_JSON OUTPUT_JSON
```

`solution.py` uses only the Python standard library. `circuits.json` contains
precomputed decompositions recovered from the supplied public target matrices.
No optimization, compilation, external packages, network access, or writes to
the submission directory are needed at runtime. The supplied two-qubit demo is
also supported.

The ordered circuits use only U3 rotations and adjacent CNOTs, with the specified
little-endian qubit order and unchanged output wire positions.

## Full-operator validation

The supplied `workspace/check.py` passes both targets:

| Target | CNOTs | U3 gates | Operator infidelity | Aligned normalized Frobenius error |
|---|---:|---:|---:|---:|
| `unitary_6q` | 36 | 78 | 5.34e-13 | 7.31e-7 |
| `unitary_7q` | 42 | 91 | 1.80e-14 | 1.35e-7 |

The complete checker report is in `validation.json`. Circuits were obtained by
numerical topology search and gate-count reduction, then polished and validated
against the entire target matrices, allowing only a global phase difference.
