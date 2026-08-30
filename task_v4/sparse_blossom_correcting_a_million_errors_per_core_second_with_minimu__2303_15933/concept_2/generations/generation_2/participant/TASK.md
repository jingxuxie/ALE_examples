# Entropy inversion under spatial calibration uncertainty — generation 2

Construct a robust counterexample to the engineering inference that a large
minimum-weight advantage reliably identifies the more probable logical class.
This challenges a confidence surrogate, **not Sparse Blossom's matching correctness**.
The graph and independent-error model follow the physical-MAP versus logical-ML
distinction in arXiv:2303.15933, sections 2.1–2.3.

Choose 39 heterogeneous edge probabilities and a spatially spread syndrome on
the fixed 20-detector, distance-six rectangular lattice. The same physical MAP
class must retain a substantial weight advantage while exact summed probability
favors its opposite, even under declared spatial calibration changes.

| Continuous domain | Certified gap | Opposite posterior | Syndrome probability |
|---|---:|---:|---:|
| Original global scale [0.95,1.05] | ≥1.08 | ≥0.85 | ≥0.0000175 |
| Declared balanced row/column calibration paths, amplitude [-0.05,0.05] | ≥0.85 | ≥0.845 | ≥0.0000175 |

There are 22 explicit spatial directions, each tested at background global scales
0.95 and 1.05. Each entire one-dimensional path is certified, **not a full
multidimensional calibration box**. Local perturbations preserve the expected
error count; they are not disguised global noise increases. Read
`workspace/SPECIFICATION.md` and `input/spec.json` for the complete domain,
artifact schema, and certificate.

The supplied actual generation-one champion passes the old task but fails this
one. `baseline/` contains that artifact and exact metrics, not a search solver.
You have **one hour of wall time**. Submit only a regular UTF-8 `witness.json`
with exactly `version`, `probabilities`, and `syndrome`; no submitted code runs.

```bash
/usr/bin/python3 -B workspace/check.py baseline/champion.json --summary-only
/usr/bin/python3 -B workspace/check.py witness.json --output metrics.json --summary-only
```

The public checker uses exhaustive nonnegative and min-plus frontier inference.
Python with NumPy suffices; no Stim, PyMatching, installation, or network is needed.
All declared certificates must pass; sampled success alone is insufficient.
