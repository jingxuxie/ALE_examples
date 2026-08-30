# Exact sliced-contraction planner

The submission entry point is `solve.py`. It reads one instance from standard
input and prints one JSON plan. It uses only Python's standard library, the
provided `contraction` module on `PYTHONPATH`, and the included native executable
`optimizer`.

The planner starts with a native reproduction of the supplied 24-trial baseline
as a regression-safe incumbent. It reproduces Python's seeded random stream and
uses exact integer arithmetic to select the baseline winner, avoiding expensive
Python baseline planning on heavily sliced inputs.
The native search combines randomized greedy contractions, annealed binary-tree
rotations, and exact dynamic programming over small contraction-tree frontiers.
Heavily sliced instances also use randomized edge-deletion search with
series/parallel graph reductions to discover much smaller slice sets.
It jointly explores slicing and contraction order, schedules ready contractions
to reduce resident memory, and retains only memory-feasible improvements. The
Python entry point checks native baseline and optimized checkpoints using the
public exact-integer cost model before selecting the final plan.

Search uses one CPU thread and a conservative 32-second native wall-clock
deadline, leaving time for input,
baseline planning, validation, and output within the 45-second invocation limit.
No network access, persistent cache, instance recognition, or stored plans are
used.

## Running

```sh
PYTHONPATH=/path/to/participant/workspace python solve.py < instance.json
```

The executable is included. Its source can be rebuilt on the supplied x86-64
environment with:

```sh
g++ -O3 -std=c++17 -mpopcnt optimizer.cpp -o optimizer
```

## Validation

`validate.py` exercises the JSON executable interface, enforces one-core affinity
and a 2 GiB address-space limit, applies a 45-second timeout, and invokes the
public `check_plan.py`. It checks feasibility and non-regression against the
baseline:

```sh
PYTHONPATH=/path/to/participant/workspace python validate.py \
    /path/to/participant/input/examples.json validation_public.json
```

`benchmark.py` provides a quicker in-process comparison. `generate_tests.py`
generates additional decorated-honeycomb instances for testing; only that
optional generator requires NetworkX. `SEARCH_SECONDS` can shorten native search
for development, and `SEARCH_DEBUG=1` enables diagnostics on standard error.

The generator accepts `large` (the default), `more`, `stress`, or `hard` as its
second argument, for example:

```sh
python generate_tests.py generated.json large
SEARCH_SECONDS=5 PYTHONPATH=/path/to/participant/workspace \
    python validate.py generated.json validation_large.json
```

## Recorded results

All recorded plans pass the public checker, satisfy their element caps, and do
not regress against the baseline. Resource-checked runs use one-core affinity,
a 2 GiB address-space limit, and a 45-second external timeout.

| Suite | Cases | Geometric-mean work reduction |
| --- | ---: | ---: |
| Provided examples | 6 | 1.375x |
| Generated larger lattices | 9 | 6.074x |
| Dimension and memory-cap stress tests | 7 | 163.104x |
| Full-size, default-budget checks | 3 | 787.059x |

The larger-lattice suite's worst bond-family improvement is 1.453x. The
default-budget public and full-size checks finish in at most 33.48 seconds.
These are measured validation results, not estimates of hidden-instance scores.

`validation_baseline.txt` records 40 cases where the native baseline reproduces
the public implementation's sliced edge set and ordered merge tree exactly.
`validation_readonly.json` records successful execution from a read-only
submission directory with a different writable working directory and exactly
one JSON output line. The other `validation_*.json` files contain per-case work,
memory, and runtime measurements. Test plans are not stored or consulted.
