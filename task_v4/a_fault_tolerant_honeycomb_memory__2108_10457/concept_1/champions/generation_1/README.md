# Correlation-aware honeycomb decoder

## Submission interface

```sh
python solve.py REQUEST_DIRECTORY OUTPUT.npy
```

The supplied workspace must be on `PYTHONPATH`, as specified by the task.
The output is a non-pickled `uint8` array with one binary logical prediction per
shot. Inference reads only the current request and the submitted implementation.
It does not load development labels, trained lookup tables, or cross-request state.

## Method

1. A deterministic ensemble of correlated matchers identifies ambiguous shots.
   The original correlated matcher remains an ensemble member.
2. Sum-product belief propagation operates on the full detector hyperedges,
   retaining the correlations represented by DEM separators instead of treating
   their graph components as independent faults.
3. Reliability-ordered GF(2) elimination produces a syndrome-consistent basis.
   A list search enumerates single changes, selected pairs, and selected triples.
   Candidate likelihoods use the original full-hyperedge error probabilities.
4. Logical-class likelihood sums account for multiple distinct corrections.
   A second propagation schedule refines low-confidence class comparisons.
5. A wall-clock budget bounds ensemble construction and list refinement.
   Any unprocessed shots retain the conservative matching-ensemble prediction.

The numerical kernels are single-threaded C++. Runtime CPU dispatch selects an
AVX2 implementation when supported and otherwise uses a generic x86-64 version.
To rebuild the included library:

```sh
g++ -O3 -funroll-loops -std=c++17 -shared -fPIC bp.cpp -o decoder_core.so
```

## Development validation

Independent Stim samples from the three supplied circuits, using seed 983714,
gave the following results on 50,000 shots per family:

| Family | Baseline failures | Submission failures | Paired wins | Paired losses |
| --- | ---: | ---: | ---: | ---: |
| EM3_v2 | 163 | 94 | 97 | 28 |
| SD6 | 83 | 34 | 62 | 13 |
| SI1000 | 158 | 32 | 136 | 10 |

The family-balanced failure ratio is approximately **0.396**, and the worst-family
ratio is **0.577**. The pooled paired improvement exceeds 13 estimated standard
errors. These are development results, not a claim about unseen evaluation cases.

Resource checks used a 60-second timeout and a 4-GiB address-space limit. They
included noisy 48-subround circuits from all three families and an extended
1,760-detector, 45,568-error-mechanism stress circuit. The largest stress request
finished in 54.2 seconds with approximately 201 MiB peak resident memory; its
time-limited refinement still improved on the original matching decoder.

Reproduce this check with the supplied assets:

```sh
PYTHONPATH="$TASK_ROOT/workspace" python development.py --task-root "$TASK_ROOT"
```

The development helper generates its own samples and writes temporary requests
under `development_work` inside the submission directory. It is not imported by
the inference entry point. Set `DECODER_DIAGNOSTICS=1` to report inference timing
and refinement counts on standard error.
