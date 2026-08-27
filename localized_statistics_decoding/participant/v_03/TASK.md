# Rescue a quantum decoder's quarantined failures

## Objective

You own the repair stage of a quantum-error-correction decoder. Its iterative
frontend provides soft information, and the shipped repair stage finds a binary
fault vector consistent with the detector record. Nevertheless, replay tests
show that this vector often lies in the wrong **logical sector**. Replace the
repair stage with a decoder that recovers these difficult frames reliably within
a practical inference budget.

This is a performance-driven scientific repair task, not a request for another
arbitrary solution of a binary linear system. You must diagnose the prototype,
experiment with materially different recovery strategies or search decisions,
and use public logical-recovery evidence to select and refine your implementation.

## The troubleshooting corpus

`input/validation_small.npz` and `input/validation_large.npz` contain 20 frames
each from two sparse quantum detector networks. Their accompanying
`*_labels.npz` files give measured logical labels for development only.
`software/solve.py`, `software/repair.py`, and `software/validate.py` provide
working I/O, the existing repair stage, and diagnostics.

These are **curated failures**, not unbiased Monte Carlo samples: the shipped
repair is syndrome-consistent but logically wrong on every frame. Independent
offline replays also establish that a lower-cost repair in the correct sector
exists. Thus the corpus is useful for diagnosing an inadequate search, but its
recovery fraction must not be reported as a physical threshold or an ordinary
channel error rate. The correct repair is not supplied.

The hidden corpus uses fresh frames, different priors and degree/geometry
configurations, and larger networks. It follows the same curation rule. You will
not receive labels, physical error histories, or a privileged decoder at runtime.

## Physical and mathematical semantics

Each frame has independent binary fault mechanisms `e[j]` with known prior
probabilities `prior[j]`. A mechanism may toggle more than two detectors, and
different mechanisms may have dependent or identical effects. All arithmetic
in the matrices is over GF(2).

- `H` is the detector-by-mechanism matrix. The observed syndrome is `H @ e % 2`.
- `L` maps a mechanism vector to a vector of logical-observable flips.
- A proposed correction `c` first needs `H @ c % 2 == syndrome`.
- It succeeds logically when `L @ c % 2 == L @ e % 2`. The right-hand side is
  provided only in development label files and hidden from deployment inputs.

Do **not** demand that a correction equal the sampled physical fault vector.
Fault vectors can differ by harmless quantum stabilizers or redundant mechanism
representations. The supplied `L` already accounts for which distinctions matter;
you need not reconstruct a stabilizer circuit or derive logical operators.

`soft_llr` is a heuristic log-likelihood-ratio diagnostic from the existing
iterative frontend: smaller values suggest a mechanism is more likely active.
It is not a second independent observation of the faults, and its confidence
can be misleading precisely on this corpus. It may be used, ignored, recomputed,
or combined with other ranking evidence as you judge appropriate. True channel
priors are in `prior`, not in a sigmoid interpretation of `soft_llr`.

The independent-mechanism negative log-probability, up to a common constant, is

```
cost(c) = sum(c[j] * log((1-prior[j]) / prior[j])).
```

It is a useful diagnostic for candidate repairs, not a substitute for logical
validation or a guarantee that a particular search attains the best sector.
Dependent checks do not provide extra independent evidence. No particular
factorization, cluster growth rule, message schedule, search order, or solver
family is prescribed.

## Interface

Submit a directory rooted at `solve.py`. The evaluator calls:

```
python solve.py --input /absolute/path/batch.npz --output /absolute/path/predictions.npz
```

Load inputs with `numpy.load(..., allow_pickle=False)`. The arrays are:

| Key | Shape | Meaning |
|---|---|---|
| `H` | `(m, n)` | binary detector matrix |
| `L` | `(k, n)` | binary logical-observable map |
| `prior` | `(n,)` | fault probabilities, strictly between 0 and 0.5 |
| `syndrome` | `(frames, m)` | binary observed records |
| `soft_llr` | `(frames, n)` | finite soft-ranking diagnostics |

Write an NPZ containing `correction`, a binary array of shape `(frames, n)`, in
the original frame and mechanism order. Equivalent corrections are accepted.
Additional numeric diagnostic arrays are permitted. There are no missing
detector observations in this task. Matrices can have substantial rank defects;
row count is not rank. Column ordering has no physical meaning.

## Deliverables and development loop

Place in the requested output directory:

1. `solve.py` and all local modules or source/build files it needs;
2. `validation_small_predictions.npz` and `validation_large_predictions.npz`;
3. `diagnosis.md`, containing actual baseline/final measurements, at least one
   failed or inferior approach you tested, the consequential choices in your
   final approach, runtime evidence, and remaining limitations.

From a workspace with the software files, for example:

```
python solve.py --input /path/input/validation_small.npz --output validation_small_predictions.npz
python validate.py --input /path/input/validation_small.npz --labels /path/input/validation_small_labels.npz --actual validation_small_predictions.npz
```

Inspect logical recovery, not just zero residual syndromes. Revise and rerun on
both public networks before finalizing. Do not embed public input or label
tables in the solver. The runtime solver must work from the five supplied input
arrays alone. A research report without an executable recovery method is not
a core deliverable.

## Environment and limits

- Python 3.10, NumPy 1.21, SciPy 1.8, the standard library, and a system C++17
  compiler are available. Local compilation is allowed. Use these libraries and
  self-contained local source or binaries in your submission; no network,
  package installation, GPU, or imports from other workspaces are allowed.
  The starter does not include a decoding library.
- Each held-out batch has 24 frames and receives **60 seconds**, one CPU thread,
  and **1.5 GiB address space**. Three batches are evaluated independently.
  Any runtime compilation is included. Training/experimentation happens earlier.
- Networks have 216--864 mechanisms and 72--288 detector rows. The number of
  logical-observable rows varies. Sparse structure and quantum degeneracy are
  important; enumerating the entire affine solution space is not feasible.
- Any strategy is allowed within these constraints. Speed alone cannot
  compensate for wrong logical sectors, and no exact optimum certificate is
  required.

## Observable success

For each hidden batch let `valid` be the fraction of syndrome-consistent frames
and `recovered` the fraction that are both syndrome-consistent and logically
correct. Its score is

```
0.15 * valid + 0.85 * min(1, recovered / 0.85).
```

The core score is the mean over the three batches. The target is at least 85%
logical recovery, full syndrome consistency, and robust execution in every
regime. Partial improvements receive real credit. Validation artifacts and a
truthful diagnostic report are also required to pass. Evaluation does not compare
your code, candidate vectors, or internal parameters with an author solution.
