# Validation results

All six circuits obey their native graphs, reach the exact ordered target matrices, and expose every required parity.
4 of six circuits also meet both resource budgets.

| Case | CNOTs / budget | Depth / budget | Both budgets |
| --- | ---: | ---: | :---: |
| ladder_12 | 102 / 204 | 31 / 37 | Pass |
| ladder_16 | 164 / 312 | 44 / 44 | Pass |
| grid_16 | 237 / 288 | 75 / 42 | Over depth |
| grid_20 | 347 / 415 | 92 / 49 | Over depth |
| branched_14 | 167 / 269 | 48 / 49 | Pass |
| branched_18 | 199 / 412 | 56 / 56 | Pass |

- Core score: 0.666667
- Worst-family score: 0.000000
- Resource score: 0.924384
- Witness size: 8277 bytes

These results come from independent exact local validation, not a hidden evaluator.
