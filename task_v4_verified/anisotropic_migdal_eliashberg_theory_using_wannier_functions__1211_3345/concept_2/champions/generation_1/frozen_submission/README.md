# Matched-normal-state witness

`witness.npz` is the submission. It contains only the float64 array `kernels`,
with shape `(2, 3, 8, 8)`. Kernel 0 has the lower transition; kernel 1 has the higher.

## Public verification

- Admissible: true; public_pass: true.
- Worst ordered ratio: **1.1245411788778297**, exceeding the target 1.12.
- Nominal M=192 transitions: **81.8854097495 K** and **92.2909269759 K**.
- Worst-case family/grid: compressed_spectrum, M=192, with transitions
  **78.6068224125 K** and **88.3966087436 K**.
- Maximum relative refinement drift: 1.893e-7, below the 0.002 limit.
- Maximum row error: 4.441e-16; maximum static error: 1.777e-15.
- Diagonal and symmetry errors: zero. Entries lie in [0.005, 5.0].

`public_check.json` contains the complete published check. Its `valid` field
remains false by design: the public checker does not run the evaluator's
independent signed-frequency and regular-row audits. Those audits have not
been run here, and no independent-audit success is claimed.

The provided repeated-reference baseline was also tested; `baseline_check.json`
records its expected admissibility, score 1.0, and failure to meet the target.

## Search

`search.py` imports the provided `workspace/physics.py` rather than implementing
another equation solver. It parameterizes the 84 symmetric off-diagonal entries,
fixes every diagonal, and imposes the labeled static and weighted-row equalities.
The equality matrix has rank 44 and a 40-dimensional null space. Bounds are
enforced by the optimizers, not by postprocessing the witness.

The low-transition kernel minimizes the supplied transition using SLSQP and
implicit gradients from the supplied eigenvalue gradients. The high-transition
kernel uses iterative linear-programming ascent over the same feasible polytope,
including 24 seeded random-vertex restarts. The search uses the compressed
spectrum with M=48; an M=192 refinement leaves both solutions unchanged.

From the participant directory, with OUTPUT set to this submission directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python "$OUTPUT/search.py" --count 48 --starts 24 --output "$OUTPUT/witness.npz"
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python workspace/check.py "$OUTPUT/witness.npz" --output "$OUTPUT/public_check.json"
```

`isolation.json` records only the two ordinary file-open error classes, in the
same order as the requested canary probes. Both probes failed before solving.
