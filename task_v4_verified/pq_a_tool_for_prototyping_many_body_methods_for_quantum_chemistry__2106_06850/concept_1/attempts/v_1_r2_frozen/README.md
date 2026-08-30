# Memory-bounded contraction planner

## Submission interface

```sh
python solve.py INPUT.json OUTPUT.json
```

`solve.py` is self-contained and uses only the Python standard library. It reads
the supplied instance and writes a declarative `{"steps": [...]}` plan. It does
not import the participant workspace, use the baseline at runtime, allocate
numerical tensors, or assume tensor symmetry.

## Planning method

- Canonicalize tensor subnetworks as connected, ordered-port graphs. Dummy
  indices, factor ordering, and output-axis permutations do not prevent reuse.
- Enumerate subset contractions and flop/peak-memory Pareto plans. For networks
  of at most six factors, also examine the complete feasible tree alternatives.
- Search batch-wide sharing choices using frequency-weighted plans,
  shared-intermediate promotion, and local replacement of individual trees.
- Schedule with explicit reference counts and bounded-cache eviction. Identical
  requested networks are computed once and emitted with the appropriate views.
- Simulate every candidate's allocations, operand lifetimes, arithmetic, and
  deletions before selecting it. The improvement search has a 20-second wall
  deadline and retains a complete valid incumbent.

All newly allocated temporaries, including final-result temporaries, count
against the cap until explicitly deleted. Inputs are permanently resident and
external emitted outputs are never used as operands.

## Supplied examples

All four supplied 20-term cases validate with the exact participant validator.

| Family | Planned FLOPs | Baseline / planned | Peak scratch elements |
| --- | ---: | ---: | ---: |
| Left/density | 4,869,000 | 1.1272 | 18,750 |
| Linear response | 14,887,500 | 1.0008 | 562,500 |
| Quadruples | 462,107,250 | 1.0299 | 562,500 |
| Right triples | 221,418,750 | 1.3462 | 562,500 |

The supplied-example geometric mean is **1.1183x**. This does not demonstrate
the task's 1.75x hidden-evaluation target; hidden-case performance is unverified.
The expanded/relabelled batches used below are correctness and scaling stress
tests, not official hidden measurements.

## Reproducible validation

Run these commands from this output directory while the participant assets
remain available at their original location:

```sh
python validation/benchmark.py
python validation/edge_check.py
python validation/canonical_check.py
python validation/stress.py 100
python validation/limit_check.py
```

The checks cover:

- The four supplied families using the exact symbolic validator.
- Twelve additional numerical cases: scalar factors, disconnected products,
  repeated factors, preserved shared output indices, implicit sums, and names
  that collide with the temporary-name prefix.
- 20,208 subnetwork comparisons against exhaustive permutation canonicalization.
- Eight 40/80-term expanded family cases and 100 randomized batches with varied
  dimensions, axis renaming, and tight memory caps.
- Three 80-term subprocess runs restricted to one CPU, 2 GiB address space, and
  a 30-second wall timeout.

Reports are in `validation/reports/`; generated cases and plans are in
`validation/artifacts/`. The optional `validation/lp_experiment.py` uses SciPy
to inspect a memory-relaxed shared-DAG lower bound; it is not a solver dependency.
