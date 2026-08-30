# Static routing-portfolio counterexample

The submission is `witness.json`. It contains the circuit, every reference SWAP,
every gate execution, and the exact final logical-to-physical mapping. Initial
placement is identity; neither an initial remapping nor a final restoration is
assumed. The reference is an explicitly feasible route, not a claim of optimality.

## Verified result

The witness uses `ladder16`, 123 demands, and 15 reference SWAPs, for 168 native
two-qubit operations. Every family passes all three resource targets.

| Relabeling family | Cheapest portfolio SWAP count |
| --- | ---: |
| identity | 76 |
| physical-11 | 75 |
| physical-29 | 74 |
| logical-47 | 76 |
| joint-71 | 73 |
| joint-103 | 72 |

The worst-family SWAP ratio is 4.8, the minimum SWAP gap is 57, and the minimum
native-operation ratio is `339 / 168 = 2.017857142857143`. The public resource
score is 1.0. All 372 portfolio routes and all six relabeled reference routes are
independently replayed by the public checker.

## Construction

The search starts with a legal physical SWAP schedule and emits demands on edges
that are native at the corresponding placements. Mutations change the native
demands and the schedule while retaining all public regularity constraints.
Candidate costs are tested against the public distance-based policies and their
physical edge orders. Final acceptance uses the unchanged public Python checker,
including all 62 policies, all six relabelings, and independent route replay.

The last three demands form a triangle on three logical wires. This triangle is
implemented with one physical SWAP: with tokens `a`, `b`, and `c` initially at a
center and two of its neighbors, execute `a-c`, execute `a-b`, swap `a` and `b`,
and execute `b-c`. The exact operand orientations and positions are in the route.

All supplied hardware graphs are bipartite, so no injective static embedding of
this logical triangle exists. The gate count is three modulo four. Consequently,
every suffix boundary examined by either embedding policy retains all three
triangle demands. Those policies cannot obtain an improving static suffix route;
their ordinary routing incumbent remains available. This observation applies
unchanged under every public relabeling and does not depend on exhausting an
embedding-search budget.

The final reference is also checked for removable SWAPs by enumerating subsequences
of its SWAP schedule and draining only dependency-ready, adjacent gates. This
changes neither the demands nor the portfolio's input. Every resulting certificate
is replayed before selection.

## Validation evidence

- `validation.json`: the unchanged public checker's result for the final file.
- `audit.json`: final file hash, regularity statistics, six reference replays,
  hardware bipartiteness, and the terminal-triangle invariant.
- `submission_summary.json`: selected candidate and minimum family resource ratios.
- `selected_result.json`: the selected candidate's complete public-checker result.

From the submission directory, the public check can be repeated with:

```sh
python -B /path/to/participant/input/benchmark.py witness.json
python -B audit.py witness.json
```

The other files are local authoring and validation tools or their outputs. No
submission code is needed to evaluate the static witness. This is a counterexample
to the supplied implementation in verification mode B, not an approximation
theorem or a claim about current tket.
