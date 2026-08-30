# A robust routing-portfolio counterexample

Construct a regular 16-qubit circuit and a cheaper, explicitly feasible SWAP route
that exposes substantial resource regret in the supplied routing portfolio.
This is verification mode B: a constructive counterexample to robustness of this
specified implementation, not a claim that the cited papers prove an approximation
guarantee or that this is the current tket implementation.

## Assets

`input/router.py` and `input/embedding.py` supply all 25 routing settings and six relabeling families.
`input/benchmark.py` is the public checker; `input/METHOD.md` explains the method
and its scope. `baseline/witness.json` is a valid but weak example, with a generator.
The participant assets are read-only. Use your writable output directory for any
search files and the final witness. Python 3 standard library is sufficient.
Your authoring limit is one hour. Submit a static witness of at most 1,000,000 bytes;
no network access or executable submission is needed.

## Interface and constraints

Submit `witness.json` in your writable output directory. It contains circuit demands
and a route, not executable submission code. Exact schemas and constraints are in
`input/FORMAT.md`. Choose one supplied sparse hardware graph. Initial placement is
fixed to identity. Preserve every per-wire dependency and execute every demand
exactly once on adjacent physical qubits; every SWAP must be a hardware edge.
Circuits have 48–200 gates, connected interactions, and moderate per-wire coverage.

## Scoring

The checker reroutes your circuit with every portfolio setting under every public
relabeling, using the **best** setting independently in each family. Pass only if,
in **all six families**, the portfolio uses at least **2.5 times your SWAP count**,
at least **16 additional SWAPs**, and at least **1.35 times your total native
two-qubit count**. One demand costs one native two-qubit operation; a SWAP costs
three. A valid but insufficient witness receives partial scores, not a pass.
No hidden answer, timing exploit, placement change, or forged cost is accepted.
