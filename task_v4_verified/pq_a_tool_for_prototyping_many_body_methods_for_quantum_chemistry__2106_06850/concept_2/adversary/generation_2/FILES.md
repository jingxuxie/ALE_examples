# Generation-two changes and records

## Active participant changes

- `participant/TASK.md`: stronger task-supplied near-Hermitian-density heuristic.
- `participant/workspace/API.md`: exact Frobenius DAD formula, endpoint bound, and source attribution.
- `participant/workspace/constraints.json`: one added key, `rdm_dad_max: 0.001`.
- `participant/workspace/oracle.py`: `rdm_dad` computed from the full unsymmetrized density.
- `participant/workspace/api.py`: finite DAD endpoint gate; original baseline inherits it unchanged.

## Active trusted changes

- `evaluator/evaluate.py`: generation-two label and independently computed DAD gate.
- `evaluator/hidden/independent.py`: independent Frobenius DAD diagnostic.
- `evaluator/hidden/constraints.json`: the same single new bound.
- `evaluator/hidden/audit.py`: DAD comparison and generation-two-only audit output paths.
- `evaluator/README.md`: current generation and manifest locations.
- `status.json`: current generation, preserved old scores, readiness, audits, and private achievability.

## New private generation-two records

- `freeze.json`, `evaluator_freeze.json`: active frozen SHA-256 manifests.
- `READY_FOR_MAIN.md`: two-replicate launch and isolation handoff.
- `SOURCE_AND_RATIONALE.md`: verified source, one-ratchet justification, and claim boundaries.
- `dad_audit.py`, `dad_audit.json`: identity, invariance, nonfinite, boundary, numerical, and security checks.
- `old_witness_rejection.json`, `*_generation_2_evaluation.json`: new-generation evaluations only.
- `preservation_before.json`: unchanged generation-one snapshot/champion hashes.
- `baseline_submission.json`, `baseline_submission.search.json`, `baseline_evaluation.json`: new baseline evidence.
- `private_feasibility.py`: private warm-start analytic-gradient search, never exposed to participants.
- `gradient_check.log`: finite-difference validation of private DAD gradients.
- `worker_feasibility_champion_high/`, `worker_feasibility_replicate1_high/`: independently passing private witnesses and CLI evaluations.

No generation-one snapshot, old attempt score, root baseline artifact, or old
champion was edited. Root generation-one manifests remain historical.
