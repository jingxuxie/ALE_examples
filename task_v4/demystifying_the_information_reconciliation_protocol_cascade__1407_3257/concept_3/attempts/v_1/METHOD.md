# Residual-channel diagnosis

## Submission

`policy.py` is the complete submission. It uses only the Python standard
library and does not read any other file, seed, label, or persistent state.

## Method

Selecting offsets 0, 2, 4, and 6 of a block intersects every possible doublet
exactly once. Consequently, after subtracting the known source contribution,
an anchor-mask parity is an exact membership test for the echo site. A mask
contains at most 16 sites, hence at most 64 selected coordinates.

The policy uses adaptive prefix decoding to identify echoes. During neighbor
discovery, already-confirmed neighbors are grouped into one query; their
individual identities need not be decoded again. Six neighbors are sought,
with three confirmations per neighbor, and a five-neighbor fallback preserves
time for classification. Decoder depth is explicitly bounded by the remaining
per-frame query allowance.

A rook neighborhood is two disjoint triangles, whereas a Shrikhande
neighborhood is a six-cycle. With one neighbor omitted, these become a triangle
plus an edge and a five-vertex path. In either case there are 10 labeled rook
patterns and 60 labeled Shrikhande patterns. The policy maintains likelihoods
over these patterns and contamination levels, including a numerical floor for
the zero-contamination case. It chooses excitation sites using expected
information gain rather than degree or common-neighbor counts.

Repeated echo evidence checks that the second neighborhood belongs to the
other component. Final inference couples the components through their shared
contamination level and the uniform prior over RR, RS, and SS. Remaining
measurements are allocated to the less certain component.

## Validation

- Public development harness: 9/9 correct, with no protocol failures.
- Fresh, balanced end-to-end test: 180/180 correct, including 20/20 in each cell.
  The test enforces the 12-second wall limit, 8-second CPU limit, and 512 MiB
  address-space limit. Its complete results are in `protocol_validation.json`.
- Decoder and model checks: 11,033 decoding cases, canonical neighborhood
  patterns, probability normalization, and joint-prior checks pass.
- Larger independent simulator validation: 1,797/1,800 correct (99.83%),
  with at least 199/200 correct (99.5%) in every cell and no protocol failures.
  Maximum CPU time was 0.624 seconds per episode. Complete results are in
  `validation_921440751.json`.

These are public-simulator validation results, not hidden-suite certification.
The validation helpers and historical experiments are not dependencies of
the submission.
