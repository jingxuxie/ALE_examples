# Reporting-only evaluator draft

This is not a new numerical task or a launch-ready ratchet. Its frozen input and numerical kernels are identical to the archived original 1.12 contract. It adds a reason on every evaluation outcome, `core_score` and `worst_family_score` with an explicit common definition, and evaluator wall/CPU/peak-RSS measurements. It leaves score computation and validity logic unchanged.

`REPORTING_REGRESSION.json` compares the original baseline and fresh champion verdicts/scores and exercises malformed, missing, and invariant-breaking artifacts. Old archived evaluation JSON and all active participant/evaluator files remain untouched. If the parent approves a scientifically evidenced new instance, this reporting implementation can be used with that separately frozen input.
