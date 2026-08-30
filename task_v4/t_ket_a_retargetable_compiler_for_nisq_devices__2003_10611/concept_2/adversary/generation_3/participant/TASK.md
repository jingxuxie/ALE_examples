# A robust routing-portfolio counterexample

Construct a regular 16-qubit circuit and an explicitly feasible cheaper SWAP route
that demonstrates substantial resource regret in the supplied routing portfolio.
This is verification mode B: a counterexample to this specified implementation,
not an approximation-theorem claim or a claim about current tket.

## Assets and interface

The read-only `input/` directory supplies the complete 62-policy router, public
checker, exact format, and method description. `baseline/witness.json` is a valid
weak example. Python's standard library is sufficient. Use only your separate
writable output directory for work and submit its static `witness.json`.
No submission code is evaluated. The authoring limit is one hour.

## Constraints

Choose a supplied sparse hardware graph. Initial placement is fixed to identity.
Use 48–200 two-qubit demands with connected interactions and moderate per-wire
coverage. Your route must execute every gate exactly once, preserve every per-wire
dependency, respect physical adjacency, and account for every SWAP. Exact schema,
regularity limits, public policy bounds, and checker commands are in `input/FORMAT.md`.

## Scoring

The checker executes all 62 policies under all six public relabelings, choosing
the cheapest policy separately in each family. Pass only if every family's
portfolio cost is at least **2.5 times your SWAP count**, at least **16 additional
SWAPs**, and at least **1.35 times your total native two-qubit count**.
Each demand costs one native two-qubit operation; a SWAP costs three.
Valid but insufficient witnesses receive partial scores, not a pass.
