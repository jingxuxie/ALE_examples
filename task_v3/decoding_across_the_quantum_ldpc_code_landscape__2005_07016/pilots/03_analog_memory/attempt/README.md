# Analog quantum-memory decoder

Run the submission with:

```sh
python solve.py --input CASE.npz --output ANSWER.npz
```

The output contains exactly `increments` and `syndrome_history`, as unsigned
binary integer arrays in the participant schema. The solver does not use case
identifiers, training data, network access, or participant resources beyond the
input case.

## Method

The Gaussian calibration is converted to signed log-likelihood ratios. Data
increments and deviations from hard readouts become variables of a sparse
space-time parity model. Its equations enforce the initial zero state, adjacent
round consistency, the supplied metachecks, and the exact terminal boundary.
The last analog readout is correctly redundant given that exact boundary.

A deterministic ensemble combines layered and flooding belief propagation,
normalized min-sum and sum-product updates, and perturbed channel reliabilities.
Nonconvergent estimates are repaired by reliability-ordered, bit-packed binary
elimination and ordered-statistics searches. Local stabilizer and temporal moves
improve the actual joint likelihood without violating the constraints.

After choosing a final recovery, class-conditional Gibbs sampling estimates
intermediate parity marginals. Rao-Blackwellized estimates and the analytically
known parity prevalence target balanced history accuracy. History decisions use
only consistency-preserving moves; the inferred final data state is unchanged.
The reported history is recomputed from the increments, and final-boundary and
metacheck consistency are checked before writing the output.

## Dependencies and limits

Only Python, NumPy, SciPy, and the supplied environment's C++ compiler are used.
`decoder.cpp` is original, self-contained C++17 code. `solve.py` builds its shared
library beside the source when needed, including compiler temporary files.
Numerical libraries are restricted to one thread. Native decoding and sampling
have separate CPU budgets, leaving headroom below the 120-second case limit.

## Validation

```sh
python test_core.py
python validate.py --exact --shots 128 --runs 32 --refine
python validate.py --family hgp --shots 128 --rounds 6 --probability .03 --runs 16 --refine
python validate.py --family toric3d --size 5 --shots 128 --rounds 6 --runs 16 --refine
python validate.py --family toric2d --size 16 --shots 128 --rounds 6 --probability .04 --runs 16 --refine
```

Tests include exhaustive small-instance MAP comparisons, forced OSD fallback,
dependent and empty metachecks, calibration reversals, deterministic priors,
high-confidence histories, terminal-readout invariance, final-state preservation,
and the exact command-line NPZ interface. Synthetic labeled memories measure
logical row-space recovery and balanced history accuracy, not just formatting.
The `example` validation family reuses only the public example's code matrices;
all its error histories and observations are generated independently.

All six regression tests pass, including 32 exhaustive MAP comparisons. Full-size
synthetic tests cover 128 shots and six rounds on 375-qubit 3D toric, 512-qubit
2D toric, and 544-qubit hypergraph-product codes. Every output satisfies the
specified consistency rules. The actual CLI invocation on the 544-qubit stress
case uses 93.81 CPU seconds and 53.2 MiB peak resident memory. A separate cold
build plus example invocation uses 2.58 CPU seconds and 138.6 MiB peak memory,
including compilation. These are validation measurements, not evaluator scores.
