# Entropy reverses logical confidence

Construct a counterexample to this proposed engineering inference: **on a local
distance-six detector lattice, a substantial minimum-weight advantage is reliable
evidence for the corresponding logical class.** This is not a claim made by Sparse
Blossom and is not a challenge to its exact matching algorithm. Sections 2.1–2.3 of
Higgott and Gidney, arXiv:2303.15933, distinguish the most probable physical error
from the most probable logical class.

Choose heterogeneous independent edge-error probabilities and a spatially spread
syndrome on the fixed 20-detector, 39-edge rectangular graph. Find a single physical
MAP class whose minimum-weight advantage persists, while the **exact sum over all
errors** overwhelmingly favors its opposite logical class. Graph topology and
logical labels are fixed; no parallel edges or invisible error mechanisms can be
introduced.

Across the entire global noise-scale interval **[0.95, 1.05]**, obtain the specified
certificate bounds: **weight gap ≥ 1.08 nats**, **opposite-class posterior ≥ 0.85**,
and **syndrome probability ≥ 0.0000175**. All three are required. The precise
schema, probability constraints, and conservative interval certificate are in
`workspace/SPECIFICATION.md` and `input/spec.json`.

You have **one hour of wall time**. Submit only a regular UTF-8 `witness.json` with
exactly `version`, `probabilities`, and `syndrome`; submitted code is never run.
The public checker is an exact inference utility, not a search solver. A valid but
weak witness and its measured results are provided in `baseline/`.

From this directory:

```bash
/usr/bin/python3 -B workspace/check.py baseline/weak.json
/usr/bin/python3 -B workspace/check.py witness.json --output metrics.json
```

Python and NumPy are sufficient; Stim and PyMatching are unnecessary. The trusted
evaluator independently recomputes all probabilities and both minimum class costs.
An artifact must pass the specified certificate, not merely sampled inversion.
