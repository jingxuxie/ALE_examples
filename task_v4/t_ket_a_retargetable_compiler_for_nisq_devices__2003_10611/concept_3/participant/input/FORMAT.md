# Exact instance and witness formats, version 1

## Public instances
`instances.json` is an object with exactly `schema_version` (integer 1) and
`instances` (an array). Every instance contains:

| Field | Meaning |
| --- | --- |
| `id` | Unique case identifier, used verbatim in the witness |
| `family` | `ladder`, `grid`, or `branched` |
| `n` | Number of physical qubits; indices are 0 through n-1 |
| `edges` | Distinct undirected native edges `[u,v]`; either control direction is legal |
| `target_rows` | n positive integer bitmasks encoding the rows of an invertible GF(2) matrix |
| `required_parities` | Distinct positive integer masks; each must occur on some wire at some prefix |
| `max_cnots` | Inclusive upper bound on native CNOT count |
| `max_depth` | Inclusive upper bound on two-qubit depth |

Bit j of a mask is the coefficient of input bit x_j. Thus mask 5 means
x_0 XOR x_2. Masks are decimal JSON integers, not arrays or strings. Rows are
ordered by physical **output** wire: y_q is the dot product of `target_rows[q]`
with x over GF(2). Input and output labels may not be permuted for free.

## Submission
Supply `submission/witness.json` under your solution directory:

```json
{"schema_version":1,"circuits":{"case_id":[[0,1],[1,2]]}}
```

Replace `case_id` and the toy gates with **all six actual identifiers** and
their circuits. `circuits` must have exactly the instance identifiers. A circuit
is an ordered array of `[control,target]` pairs, with distinct in-range integers
forming a native edge. Empty lists are syntactically legal but still undergo
all semantic tests. No other operations, ancillas, placements, metadata, phase
claims, count claims, or depth claims are accepted. Extra keys, duplicate JSON
keys, floats, booleans in integer positions, NaN, and Infinity are rejected.

The evaluator reads only this static JSON; it never imports or executes submitted
code. The filename and any untrusted submission subdirectory must not be symlinks.
For evaluator convenience an explicit regular witness file, or a directory
directly containing `witness.json`, may also be supplied to its CLI/API.

## Algebra and parity visits
Start with row masks r_q = 1 << q. For every gate `[c,t]`, perform
`r_t = r_t XOR r_c`, leaving all other rows unchanged. Check the final ordered
row list against `target_rows` exactly. Every required mask must equal a current
row at at least one prefix, including the empty prefix and the full circuit.
Visits may occur in any order, on any wire, and may repeat. The obligations are
not a prescribed sequence, and neither their order nor their original locations
are supplied. Exact Python integer XOR is sufficient for verification.

To interpret this as a phase circuit, give each required mask m its own formal
angle theta_m and insert diag(1, exp(i theta_m)) on a wire when that mask is
present, once for that obligation. The resulting basis-state phase is
exp(i sum_m theta_m * parity_m(x)) followed by the specified linear map.
This is an exact, independent-symbol obligation model, not numeric-angle
equivalence modulo 2*pi. Only parity availability is submitted and checked;
phase insertion is implicit, and single-qubit phase operations carry no charged
CNOT count or two-qubit depth. Further phase obligations are not allowed or
needed. No amplitude/statevector approximation is used.

## Scheduling and limits
Initialize `clock[q] = 0` for every wire. In submitted gate order, for `[c,t]`
set `level = 1 + max(clock[c], clock[t])`, then set both endpoint clocks to
`level`. Depth is the maximum clock, or zero for an empty circuit. Gates with
disjoint endpoints can overlap. Two gates sharing even just a control cannot
occupy the same layer. The evaluator does not commute gates sharing a wire or
perform optimizations for you. Reordering disjoint gates does not change this
depth or the available parities. There is no separate scheduling certificate.

Hard parser safety bounds: 8,388,608 bytes per file and 50,000 gates per case.
These are **not** the synthesis budgets. Both `max_cnots` and `max_depth` are
inclusive and are checked independently. Over-budget circuits may be `valid`
but are never `passed`. Out-of-format, missing-case, or oversized submissions
receive zero aggregate scores; for a well-shaped complete submission, semantic
or resource failures are scored per case.

For a semantically valid case with count C, depth D, and budgets B_C, B_D:

`efficiency = (min(1, B_C/max(1,C)) + min(1, B_D/max(1,D))) / 2`.

Invalid cases have efficiency zero. `resource_score` averages efficiency over
all six cases. `core_score` averages the Boolean `passed` indicators.
`worst_family_score` is the minimum, over the three families, of that family's
average `passed` indicator. Aggregate `valid` and `passed` are conjunctions.
The evaluator reports actual count, actual depth, missing masks, semantic
diagnostics, budget failures, and these three scores. No hidden test instances
or comparison against a secret circuit affect acceptance. The trusted evaluator
uses a frozen copy of these public targets, so changing your input file cannot
change the task.
