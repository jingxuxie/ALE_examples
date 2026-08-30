# Memory-bounded contraction planner

Run the submitted planner with:

```sh
python solve.py INPUT.json OUTPUT.json
```

The runtime files are `solve.py`, `model.py`, `optimize.py`, and
`global_lp.py`. The implementation uses Python's standard library and the
provided NumPy/SciPy installation. It does not read the participant baseline,
validator, training data, or precomputed plans at runtime.

## Planning method

- Enumerate every factor subset and binary partition of each requested
  contraction. Canonicalize tensor-network structure under dummy-index
  renaming, output-axis permutation, and permutation of identical factors.
  Tensor identity and individual tensor-axis ordering remain significant;
  no physical symmetry or equality between differently named tensors is used.
- Start with a valid, exact arithmetic/peak-memory Pareto fallback. Equivalent
  complete results are emitted together, and identical operands can share an
  allocation even within a single expression.
- Search shared contraction DAGs using amortized costs, local improvement,
  and a bounded LP-assisted branch-and-bound search.
- Schedule with memory-aware contraction trees, cache eviction, early cache
  release, and limited lookahead. Speculative schedules are checked against
  the actual live allocation count before being accepted.
- Move deletions to each temporary's final actual use. All result allocations
  are counted before operand deletion, including arrays subsequently emitted.

The anytime search retains a complete feasible incumbent and uses a 24-second
planning deadline to leave margin below the invocation limit. Optional search
results replace the incumbent only when their arithmetic cost, or then their
peak scratch allocation, is better.

## Validation

`validate_all.py` exercises the supplied exact validator, renamed and permuted
batches, large dimensions, tight memory caps, random three-to-six-factor
networks, scalar results, repeated operands, and cache-lifetime edge cases.
Its CLI subprocesses have a 30-second timeout, a 2 GiB address-space limit,
and single-threaded numerical libraries.

Public 20-term batch results:

| Batch | Arithmetic speedup | Peak scratch elements |
| --- | ---: | ---: |
| right_triples | 1.3462x | 562,500 |
| left_density | 1.1272x | 18,750 |
| linear_response | 1.0008x | 562,500 |
| quadruples | 1.0299x | 562,500 |

These small public batches have limited reuse; their geometric mean is about
1.118x, not the requested hidden-evaluation threshold. Hidden performance is
not measured or claimed here. Synthetic expanded batches are correctness and
scaling tests, not substitutes for hidden evaluation.

Detailed local measurements and generated plans are in
`experiments/validation_results.json`, `experiments_validation.log`, and
`experiments/`. The additional development scripts are not runtime dependencies.
