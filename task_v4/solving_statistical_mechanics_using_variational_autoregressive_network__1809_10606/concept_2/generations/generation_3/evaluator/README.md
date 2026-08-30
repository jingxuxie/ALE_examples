# Organizer evaluator

Run with `python -B evaluator/evaluate.py --submission DIRECTORY --output REPORT`.
This Linux evaluator reads only the size-limited regular JSON file
`DIRECTORY/witness.json`. It rejects duplicate keys, nonstandard non-finite
constants, wrong types, booleans in numeric fields, shapes, unknown fields,
non-finite or overflowing numbers, nontriangular matrices and illegal rows.
It never imports or executes code from the submission and does not use pickle.
Only installed numerical libraries and the frozen evaluator directory are used.

The evaluator checks SHA-256 commitments to the public specification and trusted
evaluation sources before evaluating a witness. Resource limits are 120 seconds
wall and CPU, 2048 MiB address space and one numerical-library thread. Reports
include resource telemetry. Isolation and process-level startup/environment
security remain the runner's responsibility; invoke from a trusted directory
with a sanitized environment and do not expose private files to participants.

Every metric uses all 2^16 states, with stable float64 log probabilities and
centered reward variance. "Exact enumeration" does not mean interval or symbolic
certification. Numerical comparison slack is fixed at 1e-10 for metric gates,
and zero for structural constraints. The public math document defines every
quantity and score. No hidden instances or learned grader are involved.

The weak baseline is expected to be valid and fail. The independent scalar,
analytic-chain, finite-difference, and malformed-input checks are in `tests/`.
Any private search results are only feasibility evidence; they never alter the
frozen goals. A missing passing witness leaves the challenge open.
