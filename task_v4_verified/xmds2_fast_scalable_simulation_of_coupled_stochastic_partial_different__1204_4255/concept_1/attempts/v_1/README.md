# Spectral representation planner

Run `/usr/bin/python3 solve.py`. The entry point accepts multiple JSON lines and
emits one `{"actions": [...]}` object for each instance. It does not import files
from the participant package or access the network.

## Assets

- `solve.py`: streaming protocol adapter and arbitrary-integer fallback.
- `planner`: statically linked Linux x86-64 planning executable.
- `engine.cpp`: complete source for the executable.

Optional rebuild:

```sh
g++ -O3 -std=c++17 -static engine.cpp -o planner
```

## Method

The planner combines shortest representation routes, routes through reusable
intermediate bases, and beam search over scratch-cache contents. Cache selection
uses field sizes, future transform distances, and version boundaries. Different
future-cost estimates are tried within a per-instance CPU budget. Large cache
sets use marginal-value eviction instead of exponential subset enumeration.

Search cutoffs finish the remaining reads with a valid baseline continuation.
The complete frozen-baseline policy is also evaluated, and a more expensive
candidate is never selected. Large integer costs are reduced by their common
divisor when possible; otherwise the Python implementation of the baseline is
used without narrowing the integers.

## Validation and limitation

The supplied ten examples pass the supplied plan checker. Additional tests cover
all supported dimension counts, tight and generous capacities, updates, empty
and home-only traces, multiple input lines, and very large integer costs, under
a 1 GiB address-space limit.

The observed geometric-mean cost reduction on the supplied examples is about
17.6%. This is below the requested 20% target; held-out performance is not known.
