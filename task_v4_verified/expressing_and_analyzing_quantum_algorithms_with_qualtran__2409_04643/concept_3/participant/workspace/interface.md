# Exact interface

`input/suite.json` contains `instances`. Each has an `id`, `family`, address
width `n`, output width `m`, integer `table`, and resource `caps`. Row `address`
specifies the output integer. Both address and output bits are little-endian.

Submit `{"circuits": [{"id": "...", "gates": [...], "outputs": [...]}]}`.
There must be exactly one circuit for each supplied ID and no others. Each gate
is `{"left": [references], "right": [references]}` and computes the AND of
the two indicated XORs. An empty XOR is zero. Reference 0 is constant one;
references 1 through n are address bits 0 through n-1. Gate number j (zero-based)
creates reference n+1+j, and its inputs may use only earlier references.
Every affine list must be sorted, duplicate-free strict integers; booleans and
floating point values are rejected. `outputs` has m affine lists in bit order.

Resources are counted from this representation, not from declared metadata:
- `and`: number of product gates.
- `depth`: maximum multiplicative depth of all gates and output expressions.
  Inputs and constants have depth zero; XOR takes maximum; each AND adds one.
  This is NOT physical circuit depth.
- `affine`: total number of references in all gate operands and outputs.
- `ancilla`: zero if there are no products, otherwise number of products plus
  two, for the mandated retain-products/two-scratch clean reversible lift.

The clean oracle computes these products into fresh bits, XORs outputs into an
arbitrary target register, and reverses all products. It preserves the address
and clears scratch. The convention charges two Toffolis per product across
compute/uncompute. All four caps must hold; no alternative uncomputation model
or approximate answer is accepted. The exhaustive Boolean truth-table equality
therefore also specifies the coherent oracle on superpositions by linearity.

The evaluator accepts at most 50,000 gates per circuit for diagnostics, but the
instance caps are much tighter. Duplicate JSON keys, nonfinite values, extra
fields and symlink artifacts are rejected. Core score is the fraction of the six
instances that are both exact and within every cap; passing requires 1.0.
Worst-family score is the minimum within-family passing fraction. Correctness
fractions and resource usage are also reported. No reference implementation is
needed for verification.

```
python3 baseline/solve.py --input input --output /YOUR_OUTPUT/circuits.json
python3 workspace/verify.py --input input --submission /YOUR_OUTPUT
```

The baseline is exact shared algebraic-normal-form synthesis; it need not meet
the resource budgets. The private evaluator uses an immutable checker and input
copy. Evaluation takes at most 60 seconds and never executes submitted code.
