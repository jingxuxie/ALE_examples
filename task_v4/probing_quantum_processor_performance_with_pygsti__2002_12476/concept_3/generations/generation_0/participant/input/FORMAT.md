# Array and prediction formats

All inputs are NumPy NPZ archives readable with `np.load(path, allow_pickle=False)`.
Arrays have no object dtype. Each archive contains these aligned arrays:

| key | shape | meaning |
|---|---|---|
| `ids` | (N,) int64 | unique row ID within this split |
| `device` | (N,) int8 | device 0 through 3 |
| `time` | (N,) float64 | normalized acquisition time |
| `preparation` | (N,) int8 | 0:+X, 1:-X, 2:+Y, 3:-Y, 4:+Z, 5:-Z |
| `measurement` | (N,) int8 | 0:X, 1:Y, 2:Z |
| `length` | (N,) int16 | number of gates |
| `gates` | (N,max_length) int8 | ordered gate codes, padded with -1 |
| `family` | (N,) fixed-width Unicode | announced query family, `calibration`, or `random` |

Labeled archives additionally contain `shots` and `count_one`, both (N,) int64.
They contain no exact probabilities or physical parameter values. Empty circuits
have length zero; ignore all padded gates. No training/development/test records
share the complete tuple `(device,time,preparation,measurement,gate_string)`.
Distinct rows can legitimately share a gate string at different contexts.

Submission is UTF-8 JSON with exactly two keys:

`{"ids": [0, 1], "p1": [0.25, 0.72]}`

The example is illustrative, not a complete submission. Include all IDs from
`queries.npz` exactly once. IDs must be JSON integers, not booleans or numeric
strings. Probabilities must be JSON numbers, not booleans or strings. Duplicate
keys, duplicate IDs, missing/extra IDs, NaN, infinity, out-of-range probabilities,
wrong dimensions, and files over 2 MiB are invalid. Submit a self-contained regular
file; symbolic links and other non-regular files are rejected. Additional files or
executable code are not inspected by the evaluator.

The supplied baseline accepts `--split development` to emit development
predictions. Score them with:

`python workspace/score_development.py --input input/development.npz --submission /YOUR_OUTPUT/dev.json`

Development diagnostics compare against counts and also estimate the shot-noise
contribution. They are not the exact private score and should not be treated as
an evaluator oracle. Acquisition times lie in the same interval in all splits.
