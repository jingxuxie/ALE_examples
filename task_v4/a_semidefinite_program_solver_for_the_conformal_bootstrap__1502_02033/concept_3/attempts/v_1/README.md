# Submission status

Exactly certified blocks: 2 / 3.

This is a partial result, not a complete solution to TASK.md.
The third block contains a high-precision rational approximation, not an exact positivity certificate.

## Verification

`python ../../participant/workspace/check.py ../../participant/input/instances.json certificate.json`

Artifact size: 56188 bytes.
Maximum rational numerator/denominator size: 368 bits.

The supplied exact checker report is saved in `check_report.json`.

## Reconstruction

- The first block uses recovered integer factors divided by 8.
- The second block uses a three-column factorization and the exact polynomial column relation
  `column_4 = (x+1) column_1 + (x^2-x+2) column_2 + (2x-1) column_3`.
- The third block is transformed using exact dyadic column operations and the variable substitution `x = 2t`.
- `assemble.py` reproduces the artifact from the saved reconstruction data.
- All exploratory programs, intermediate factors, and logs are retained in this output directory.
