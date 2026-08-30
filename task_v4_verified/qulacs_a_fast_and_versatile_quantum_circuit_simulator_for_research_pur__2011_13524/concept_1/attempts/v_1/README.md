# Structure-aware circuit fusion

Run the standalone planner with:

```sh
python3 solution.py INPUT_JSON OUTPUT_JSON
```

The input and output follow `TASK.md`'s batch interface. The implementation uses
only the Python standard library. All required modules are in this directory;
there are no runtime references to the participant directory or to test data.

## Planner

- Retains all seven supplied baseline orderings, with optimal contiguous
  partitioning and independent selection across barrier-separated epochs.
- Builds fusible dependency closures rather than relying only on recent gates.
  Dense, diagonal, and permutation construction costs are all charged explicitly.
- Searches alternative block frontiers in both directions, including separate
  homogeneous-support searches when dense matrix construction is expensive.
- Refines legal schedules through dependency-constrained gate reassignment,
  block contraction, and bounded two-block support repartitioning problems.
- Uses up to four worker processes, bounded per-case searches, an overall
  deadline, and legal anytime completions. A second refinement pass uses spare
  batch time without replacing a schedule by a more expensive one.
- Independently validates every returned worker result against the supplied
  public resource model and retains a baseline fallback.

`baseline.py` and `model.py` contain the supplied public baseline and checker.
The other supporting modules implement the searches described above.

## Validation

The official public checker accepted every schedule on the supplied examples.
Additional tests exercised 60 randomized circuits, including very short search
budgets, and a locally generated 25-case batch spanning the published circuit
sizes and all five structural patterns. Test inputs and cached schedules are not
needed by the executable.

Recorded local results (modeled speedup, not simulator wall speed):

- Supplied five-case examples: **1.21669×** geometric-mean speedup, all valid.
- Generated 25-case stress batch: **1.20515×**, all valid, **125.3 s** wall time.
- Maximum-size batch: **25 × 1,500 operations**, all valid, **165.5 s** wall time.
- Sixty additional randomized cases passed legality checks, including deliberately
  interrupted searches and reverse planning.

Timings depend on the host. Hidden-case performance was not measured.
