# Calibration-aware routing engine

Run one instance through standard input:

```sh
python3 solve.py < instance.json > route.json
```

`solve.py` uses only the standard Python runtime and the included, statically
linked Linux x86-64 `router` executable. It does not read instance collections,
reference scores, network resources, or calibration data outside the current
input. The instance identifier and architecture-family label are not used by
the optimizer.

## Method

The router partitions the program into embeddable interaction blocks involving
at most four logical wires. It combines recurring blocks only when intervening
operations are independent, then searches dependency-preserving block orders.
Every original gate is retained with its original index and operand orientation.

For each block, a multi-source shortest-path computation on partial placements
finds the exact minimum of calibrated SWAP work and the block's aggregate gate
work among plans that relocate the block before a fixed-placement execution.
Each transition is a real hardware-edge SWAP. Unconstrained wires remain
fully tracked in the emitted route; the initial placement is never changed for
free. Weighted lookahead and stochastic rollouts account for future blocks.

A second search examines alternative destination embeddings and their actual
effects on all wires. It can pre-position incoming operands before relocating a
block, avoiding unnecessary displacement across expensive edges. Candidate
routes are compared using calibrated work plus `0.05 * depth`, including all
relocation operations. No gate cancellation or resynthesis is performed.

Search is bounded by wall-clock deadlines and cache limits. For programs with
many distinct interaction blocks, a valid fallback combines exact two-token
routing with calibrated dependency-frontier routing. The normal search budget
is 7.5 seconds, and converged searches stop earlier. Development runs may set
`ROUTER_BUDGET` and `ROUTER_DEBUG`; neither is needed for normal operation.
The Python entry point independently checks the complete route before emitting
it. A bounded shortest-hop fallback also handles backend failures or timeouts.

## Build

The executable is already included. To rebuild it on a compatible toolchain:

```sh
g++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -static -s router.cpp -o router
```

## Validation

The public benchmark validates hardware adjacency, every gate's uniqueness and
wire dependencies, the fixed initial placement, the operation limit, calibrated
work, and depth independently of the router:

```sh
python3 benchmark.py /path/to/participant/input --budget 7.5 --output results_full.json
python3 test_router.py /path/to/participant/input --output stress_results.json
```

The twelve public cases achieve a 68.5% geometric-mean cost reduction. Family
reductions are 57.3% chain, 58.1% ring, 76.3% grid, 77.7% ladder, 60.8% tree,
and 73.8% modular. All twelve routes pass validation.

The stress suite includes 24 independently relabeled public cases, 21 random
programs on connected graphs, and five additional edge cases. Each invocation
is checked with a 12-second timeout and a 2 GiB address-space limit. Measurement
details are recorded in `results_full.json` and `stress_results.json`.
The tests also exercise backend-failure recovery and the bounded Python
fallback. Undefined-behavior and bounds-sanitizer runs cover public examples
and a dense graph with more than 64 edges.

The final public run takes 35.3 seconds in total, with a maximum of 5.40 seconds
per instance. The final stress run's maximum is 5.08 seconds. A separate
28-wire modular run measures 49,400 KiB peak resident memory. The complete
submission occupies approximately 2.1 MiB.
