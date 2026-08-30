# Finite-lookahead routing counterexample

The submission is `witness.json`, a static circuit and complete physical route
certificate. It starts at identity, preserves all per-wire dependencies, and
uses only native adjacent gates and hardware-edge SWAPs. No optimized initial
placement, executable submission, or externally supplied cost is used.

`verification.json` records the circuit's regularity statistics and the complete
public-checker results for all 108 routes (18 settings in each of six relabeling
families). `result.json` is a separate run of the unmodified public checker on
the final file. The verification report includes the witness's SHA-256 digest.

## Verified result

The final circuit contains 80 demands on `ladder16`. The reference uses 8 SWAPs
and 104 native two-qubit operations. In **each of all six relabeling families**,
the cheapest of the 18 portfolio settings uses 66 SWAPs and 278 native two-qubit
operations: an 8.25-fold SWAP ratio, a 58-SWAP gap, and a native-operation ratio
of approximately 2.6731. Every family's cheapest route uses zero fallback SWAPs.

The unmodified checker reports `valid: true`, `passed: true`, and all three
scores equal to 1.0. All 16 wires have 4–17 incident demands and 2–4 distinct
partners; the connected interaction graph has 23 distinct pairs, each occurring
at most six times. The final file is a regular 7,408-byte JSON file.

## Recheck

From this directory:

```sh
python3 -B ../../participant/input/benchmark.py witness.json
python3 -B verify.py witness.json --output verification
```

Both commands use only the supplied participant assets and the submission
directory. The first command does not depend on any compiled search component.

## Construction and search

`search.py` generates legal physical schedules and derives logical demands by
tracking the occupants of every hardware node. It filters circuits through the
supplied validation rules before evaluating them. `improve.py` refines gate
choices, gate order, and SWAP placement while retaining a feasible certificate.
The reference uses eight SWAPs, the smallest count allowed by the task.

`router_fast.cpp` accelerates the exact public routing rules for search; it is
not part of the submission interface. Its counts were cross-checked against
1,620 public Python routes covering every hardware graph, every portfolio
setting and relabeling, and initial, early, phased, and distributed SWAP
schedules. Promising candidates and the final file are additionally checked
against the complete public Python portfolio, including independent route
replay. No evaluator-private files, networks, or external routing solvers are
used.

The search utilities can be rebuilt and exercised with:

```sh
g++ -std=c++17 -O3 -ffp-contract=off -fPIC -shared router_fast.cpp -o router_fast.so
python3 -B search.py --graph ladder16 --check 2
python3 -B search.py --graph ladder16 --seconds 180 --tag random-ladder
python3 -B improve.py random-ladder.json --seconds 120 --tag improved-ladder
```

This is a counterexample only to the specified finite-lookahead SWAP-routing
portfolio, not to the current tket implementation or an approximation theorem
in the motivating papers. No optimality claim is needed for the reference
route: it is an explicitly replayed upper bound.
