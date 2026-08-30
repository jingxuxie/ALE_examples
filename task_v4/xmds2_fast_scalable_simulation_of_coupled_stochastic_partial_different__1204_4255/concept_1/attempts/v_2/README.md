# Spectral representation planner

Run the submission with:

```sh
/usr/bin/python3 solve.py < instances.jsonl
```

`solve.py` accepts and returns one JSON object per line. It launches the supplied
Linux x86-64 `planner` executable once and streams instances through it. No
participant-package imports, network access, or runtime compilation are needed.

The native planner combines exact directed transform distances, cost-aware
offline eviction, forward representation-cache beam search, and backward
shared-ancestor search. It can connect compatible forward prefixes and backward
suffixes. Search widths adapt to an elapsed-time budget. An independently simulated
baseline plan remains available as a fallback; cheaper candidates undergo a
full representation, update, scratch-memory, and cost check before selection.

All ordinary benchmark costs are represented exactly. The Python adapter only
rescales exceptionally large costs above 10^12 to avoid native integer overflow;
it does not change the action semantics.

Rebuild the included executable from its source with:

```sh
g++ -std=c++17 -O3 -flto -static -s planner.cpp -o planner
```

The provided public checker validates all ten examples. The measured public
geometric-mean cost reduction is approximately 18.1%; this does not establish
the requested 20% reduction on unseen instances.

Additional validation covers 32 randomized instances with 3–6 dimensions and
10 stress cases, including minimal capacity, frequent updates, tied costs,
home-only reads, large capacity, and very large integer costs. A 100-instance
stream of repeated public examples passes every plan check in 51.1 seconds
under a 1 GiB address-space limit, with approximately 52 MiB peak resident
memory. These are local measurements, not held-out evaluation results.
