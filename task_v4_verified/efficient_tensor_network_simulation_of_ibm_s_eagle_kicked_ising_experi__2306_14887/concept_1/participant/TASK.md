# Exact contraction beyond the tree approximation

Improve the supplied planner for exact, sliced contraction of double-layer
tensor networks on decorated honeycomb (heavy-hex) graphs. These networks model
the expensive environment contractions needed to check a belief-propagation
simulation; tensor values are immaterial to the planning objective.

Provided: an executable baseline, a public cost checker, and representative
instances in `input/examples.json`. The schema and arithmetic/storage convention
are specified in `input/FORMAT.md`. All instances have maximum degree three,
edge dimensions 4, 16 or 64, and open boundaries, optionally with corner leaves.
Hidden instances cover balanced, directional and inhomogeneous bond dimensions
on lattices with 3--5 rows and 3--6 columns of hexagons, with relabeled vertices.

Submit `solve.py` and any dependencies in the output directory. It must read one
instance as JSON from stdin and write one JSON plan to stdout. A plan specifies
sliced edge IDs and an ordered binary contraction tree. Only the final JSON may
appear on stdout. The supplied workspace is available on `PYTHONPATH`.
Submission files are read-only during scoring; the working directory and `/tmp`
are writable. Sandbox setup is excluded from the per-invocation planning timer.

Each invocation gets one CPU thread, 45 seconds wall time and 2 GiB address space.
External services and stored answers for test instances are prohibited. Planning
runtime and contraction memory feasibility are checked separately from modeled
contraction work. The input's element cap must hold for every contraction step.

The fixed improvement target is at least **4x geometric-mean modeled work
reduction** relative to the supplied baseline, at least **1.1x within every bond
family**, and no individual case more than **5% worse**. All plans must be valid
and memory-feasible. Scores also report runtime, the worst family and regressions.
