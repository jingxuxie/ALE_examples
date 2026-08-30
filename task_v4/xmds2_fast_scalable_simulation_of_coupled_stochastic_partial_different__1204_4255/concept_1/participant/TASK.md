# Spectral representation scheduling

Build a memory-bounded planner for a spectral simulation compiler. Repeated field reads require different tensor-product bases and distributed layouts, while field updates invalidate cached representations.

The package provides a fully specified integer-cost execution model, representative traces, a plan checker, and a runnable shortest-route/offline-eviction baseline. This is a compiler-planning benchmark motivated by XMDS2, not a request to reproduce XMDS2.

Submit `solve.py` and its required assets in your output directory. The evaluator sends one instance per JSON line on standard input; return one JSON object containing `actions` per line. The process must handle multiple instances. See `input/protocol.md` for exact semantics.

Every plan must preserve all requested representations and obey the scratch-memory ceiling. On held-out traces, achieve at least **20% geometric-mean cost reduction** relative to the supplied baseline, with at least **8% reduction in every workload family**. Total evaluation budget: 120 seconds on one CPU, 1 GiB address space, no network. Correctness, execution cost, worst-family performance, and planning resources are scored. You have one hour to develop your submission.
