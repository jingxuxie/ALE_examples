# Sparse recovery submission

Run `python solve.py --input CASE.npz --output ANSWER.npz`.

The service uses NumPy and a single-core C++17 decoder. The supplied native
library is cached; if missing or older than `decoder.cpp`, `solve.py` rebuilds
it with the installed `g++`. Compilation, Python startup, and decoding are
charged against the supplied CPU budget. Compiler temporary files stay in
this directory. No network access or specialized decoder packages are used.

## Decoder

- Normalize probabilities above one half by a deterministic baseline flip.
  Combine identical syndrome columns using their exact independent parity
  probability, retaining a maximum-probability representative for expansion.
- Run damped normalized min-sum belief propagation, with averaged soft
  information and syndrome checks after each iteration.
- For failures, grow reliability-ordered local clusters from syndrome defects.
  Meldable boundary heaps and union-find merge intersecting clusters. Sparse
  incremental GF(2) column elimination maintains the residual and a valid
  correction without refactorizing clusters on merges.
- Improve solutions with local nullspace cycles and within-cluster order-two
  searches. Small matrices additionally receive bounded, bit-packed OSD
  searches. Budgeted layered-min-sum and sum-product restarts supply alternative
  reliability estimates. Candidate selection uses the actual prior likelihood.

Large matrices never enter the global OSD path: it is limited to at most 1,200
checks and 5,000 grouped variables. Runtime allocation adapts to the remaining
shots and CPU allowance. `DECODER_STATS=1` prints diagnostics to stderr.

## Validation

After the library has been built:

```
python check_edges.py
python validate.py --shots 100
python validate.py --large --shots 100
python stress_validate.py --cold
```

Tests check actual GF(2) syndromes and logical recovery, not just NPZ shape.
They include hypergraph-product stabilizer equivalence, sparse high-rate
matrices, spatial and repeated-extraction-style detector graphs, nonuniform
priors, duplicate columns, dependent checks, permutations, empty dimensions,
and probabilities zero, one half, and one. The small exhaustive test compares
against all 65,536 possible errors and recovers a likelihood-optimal correction
on 299 of 300 sampled shots.

The full-size CLI test uses 400 shots, 20,000 active checks, and 250,000 nonempty
fault columns. Detector columns are duplicated with exact parity aggregation;
both rows and columns are randomly permuted. Hidden-from-the-decoder logical
observables are checked after recovery. Its cold mode also tests compilation
inside a 30-second CPU allowance and the 1.5-GiB memory limit.

The final cold full-size run recovered all 400 syndromes and all 400 logical
outcomes in 29.24 CPU seconds (29.43 wall seconds), including compilation and
startup, with approximately 250 MiB peak child RSS. A separate 20-shot test
with 250,000 distinct weight-four columns and 20,000 checks recovered every
actual fault vector in 0.93 CPU seconds through the native interface.

In the 1,100-shot family regression, every correction satisfied its syndrome.
For example, logical successes were 57/100 versus the weak decoder's 14/100
on a 720-variable hypergraph product, and 100/100 versus 3/100 on an
847-check repeated-extraction-style detector graph. These are synthetic local
validation results, not claims about the unavailable private evaluation.

The supplied `example.npz` contains inconsistent syndromes: exact GF(2)
column-space testing finds only zero-based shot 10 feasible. Thus no decoder
can satisfy the other 11 rows. The service reports such inconsistent rows on
stderr while still producing the required binary output; validation uses
independently generated, consistent instances for recovery measurements.
