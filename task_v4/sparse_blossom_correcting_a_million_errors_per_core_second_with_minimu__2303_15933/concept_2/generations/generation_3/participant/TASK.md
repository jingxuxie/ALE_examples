# Entropy inversion under position-dependent anisotropy — generation 3

Construct a counterexample to the inference that a large minimum-weight advantage
reliably identifies the more probable logical class. This challenges a confidence
surrogate, **not Sparse Blossom's matching correctness**. The independent-error
model follows the physical-MAP/logical-ML distinction in arXiv:2303.15933,
sections 2.1–2.3.

Choose 39 heterogeneous edge probabilities and a spread syndrome on the fixed
20-detector, distance-six rectangular lattice. A fixed physical MAP class must
retain a substantial weight advantage while exact summed probability favors its
opposite throughout every declared calibration path.

| Continuous domain | Certified gap | Opposite posterior | Syndrome probability |
|---|---:|---:|---:|
| Global noise scale [0.95,1.05] | ≥1.08 | ≥0.85 | ≥0.0000175 |
| Balanced spatial and orientation-conditioned paths | ≥0.85 | ≥0.845 | ≥0.0000175 |

All previous requirements remain. The extension adds 43 explicit directions
combining horizontal/vertical contrast with row, column, and crossed-lane fields.
Each is tested continuously at amplitudes [-0.05,0.05], at both background scales
0.95 and 1.05. Local changes preserve the expected error count and never exceed
5% per edge relative to their background. This is a union of **131 continuous
one-dimensional paths**, not a full multidimensional calibration box.

The actual generation-two champion in `baseline/` passes the previous task but
has genuine pointwise failures in this one. Achievability of all strengthened
conditions is currently **unknown**; the baseline is not a feasibility witness.
The packet contains no search solver. See `workspace/SPECIFICATION.md` and
`input/spec.json` for the complete domain, JSON schema, and sufficient certificates.

You have **one hour of wall time**. Submit only a regular UTF-8 `witness.json`
with exactly `version`, `probabilities`, and `syndrome`. No submitted code runs.

```bash
/usr/bin/python3 -B workspace/check.py baseline/champion.json --summary-only
/usr/bin/python3 -B workspace/check.py witness.json --output metrics.json --summary-only
```

Python with NumPy suffices. No Stim, PyMatching, installation, or network is
needed. All declared certificates must pass; sampled success alone is insufficient.
