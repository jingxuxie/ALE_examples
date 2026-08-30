# Response completeness and infeasibility audit — August 28, 2026

**Conclusion: the frozen concept is infeasible, not merely difficult.** For every
declarative plan accepted by the supplied validator on each of the six response
cases, the bounds below apply. Response-family geometric-mean speedup is at most
**1.022753055829×**, below the required **1.15×**. The simpler exact statement
that *every response case has speedup strictly below 1.06×* already proves
failure of that family gate, independently of the overall 1.75× target.

This supersedes the preliminary portfolio's deliberately cautious “unknown”
assessment. Participant, evaluator, original manifest, and targets were not
modified; no tested-attempt contents were read.

## Why the graph covers every useful legal plan

The checked cases have distinct axes per primitive factor, each index occurs
once (an output index) or twice (a summed index), and every term has 3–5 factors.
The argument is about the actual validator's exact monomial semantics, not
assumed numerical identities or tensor symmetry.

1. **Unroll uses, not buffers.** Remove operations with no path to an emitted
   result. Unroll each remaining output's dependency DAG into a binary tree;
   using one temporary twice creates two occurrences of its factors. Every
   binary step concatenates factor lists without cancellation. Validator
   equality supplies a name/axis-position-preserving isomorphism from the
   expanded output to the requested term. Thus every intermediate occurrence
   corresponds to a nonempty subset `S` of that term's *labeled factor
   occurrences*, including multiplicities. Extraneous factors cannot disappear.

2. **The boundary states are exhaustive.** Let `I(S)` be the indices incident
   to `S`, and `R(S)` those also needed outside `S` or in the requested output.
   A useful intermediate's boundary is exactly
   `B = R(S) ∪ K`, for some `K ⊆ I(S) \ R(S)`.
   A closed index is renamed freshly on each operand resolution; it cannot
   reconnect to another operand or reappear as a free index. Conversely, two
   distinct ports already inside one intermediate can never be merged later:
   every operand binding is injective, and repeated axes within an operand are
   rejected. Consequently a pair destined to share a final index must already
   share one label when its occurrences first enter the same subtree. Keeping
   that paired label open is precisely a retained internal index in `K`.
   Splitting it into two ports for a later diagonal is not a legal escape.

3. **Every useful binary operation is enumerated.** Its occurrence subsets
   partition `S` into disjoint nonempty `L,R`. Both child boundaries are states
   from item 2; the parent boundary is any permitted subset of their union.
   Its exact cost is the product of the union's dimensions, doubled iff any
   union index is omitted. The unpruned enumeration visits every such split
   and boundary choice, including disconnected products, delayed sums, scalars,
   and equal semantic children. Tensor names and axis positions fix index types.

4. **Global reuse and recomputation do not invalidate the relaxation.** Merge
   states only under tensor-factor commutation, dummy renaming, and free-port
   permutation. The canonicalizer is complete for these isomorphisms: enumerate
   factor orderings, then assign labels on first occurrence with boundary versus
   internal roles distinguished. Choose one actually used construction for each
   semantic value in a valid plan. Its children have strictly fewer factors,
   so these choices form an acyclic global graph. Their total arithmetic is no
   greater than the original plan's: repeated constructions are paid only once.
   All requested root classes are present. This remains true when a value is
   used twice in one operation, with different bindings, or across outputs.

5. **No schedule or memory assumption is needed.** The certified graph disables
   all memory pruning: its construction cap is at least three times the largest
   whole-term index volume, exceeding every possible parent-plus-two-operands
   allocation. An independent check confirms that *zero* edges are removed.
   Lifetimes, recomputation, step limits, planner time, and the actual scratch
   cap are relaxed, never strengthened. Therefore every valid bounded-memory
   plan maps to a feasible integer selection of this graph with no greater cost.

These items establish a universal lower-bound relaxation for the frozen cases.
There is no remaining useful legal monomial-plan class outside the enumeration.
The conclusion is specific to this validator and these hashed inputs; adding
unary operations, diagonal bindings, addition, slicing, or numerical identities
would require a new audit.

## Exact certificate, not solver status

For binary-edge variables in `[0,1]`, each requested root selects one outgoing
construction, each other node selects at most one, and every selected edge
requires its nonprimitive children. Item 4 maps every valid plan into this model.
Saved integer multipliers yield the exact Lagrangian lower bound
`constant + Σ min(0, reduced_cost)`. Inequality multipliers are nonpositive;
root-equality multipliers are unrestricted. All checking uses Python integers.
Edges costing more than the certificate cutoff are safely handled by capping
the lower bound at that cutoff: any selection using an omitted edge already
costs more. Floating-point LP or branch-and-bound optimality is not assumed.

| Response case | Frozen baseline FLOPs | Universal FLOP lower bound | Speedup upper bound |
|---|---:|---:|---:|
| 0 | 5,046,912 | 4,765,056 | 1.059150616489 |
| 1 | 1,082,900,480 | 1,055,219,712 | 1.026232231720 |
| 2 | 55,177,293,312 | 54,530,661,888 | 1.011858125349 |
| 3 | 70,489,920,000 | 69,254,080,000 | 1.017845013608 |
| 4 | 8,406,588,240 | 8,283,695,040 | 1.014835553387 |
| 5 | 623,998,083,072 | 619,382,407,168 | 1.007452061684 |

Displayed upper bounds are rounded upward. For every row the verifier checks
`50 × baseline < 53 × lower_bound` exactly. It also checks
`20^6 × Π baseline < 23^6 × Π lower_bound`, and the analogous comparison against
the manifest's exact binary-float representation of 1.15. The family bound is
the sixth root of the exact rational product stored in the JSON reports; its
decimal approximation is not used to establish infeasibility.

## Omitted-mechanism audit

| Mechanism | Finding |
|---|---|
| Same temporary used twice | Included. Actual local allocation charges the buffer once, not twice; both original pruning sites use a set of child IDs. Universal bounds additionally remove all memory pruning. |
| Rebinding, transposed views | Included by free-port permutations and per-use bindings. A shared matrix used as `M_ij M_ji` validates at peak 5, not a double-counted 9. |
| Dummy labels in repeated uses | Fresh per operand, exactly as the validator requires; two copies do not accidentally share their already-summed variables. |
| Retained internal indices | Included for every retained subset. A Hadamard intermediate followed by a later sum validates and is present. |
| Closing and reopening an index | Not legal: closed variables become inaccessible internal namespaces; rank-changing rebinding is rejected. |
| Splitting an index, merging later | Not legal within an existing operand: repeated-axis bindings are rejected; separate premature sums fail exact equality. |
| Emitted output as free cache | Not legal after deleting its source temporary; the external output store cannot be addressed as an operand. A retained source still counts as scratch. |
| Different trees, arbitrary term order, eviction | Covered by the global selection relaxation; discarding lifetime constraints and duplicate computations can only lower cost. |

Eight direct validator fixtures pass their expected outcomes, including four
valid alias/retention plans and four rejected escape mechanisms. They are saved
with complete cases, plans, and exact results in `mechanism_fixtures.json`.

## Independent checks and reproduction

An occurrence-mask enumerator independently checks **5,714 state witnesses** and
**28,874 binary-operation witnesses**, merging to **3,946 nodes / 26,830 edges**
across the six unpruned cases. A different canonicalizer permutes *all* factor
occurrences and colors boundary roles; its classes are bijective with the
solver's. Every state's ordered canonical form is also checked against
`contract.canonical`, and root demands and all edge/cost signatures agree.
All six baseline costs and saved valid witnesses are revalidated.

From the private portfolio directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python -S response_completeness.py --verify-only
```

This succeeded with **no SciPy import** and no optimizer invocation; exact
runtime is recorded in `response_universal/verified_summary.json`. It
regenerates the entire unpruned graph, repeats the independent
enumeration and fixtures, checks all integer certificates and exact target
inequalities, and rejects changed validator/manifest/checker hashes. Original
case hashes are checked against each certificate package.

Artifacts: `response_universal/summary.json`, `verified_summary.json`, six
`linear_response_*.unbounded.bound.json` packages, and
`mechanism_fixtures.json`. **The response gate alone certifies rejection of the
frozen concept; this result should not be labeled participant difficulty.**
