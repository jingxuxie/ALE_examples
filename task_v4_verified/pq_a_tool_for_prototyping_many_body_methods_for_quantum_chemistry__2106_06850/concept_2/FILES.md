# Package map

## Frozen participant files

- `participant/TASK.md`: concise high-level falsification task.
- `participant/workspace/API.md`: complete Hamiltonian, amplitude, score, path, and JSON contract.
- `participant/workspace/constraints.json`: all fixed numerical thresholds.
- `participant/workspace/oracle.py`: determinant-space CCSD/lambda/RDM/EOM/FCI oracle.
- `participant/workspace/api.py`: artifact construction, endpoint screening, and path checks.
- `participant/workspace/probe.py`: runnable public diagnostic command.
- `participant/workspace/example.json`: valid noninteracting, nonpassing artifact.
- `participant/baseline/search.py`: reproducible random-search starter.
- `participant/baseline/run.sh`: baseline launcher.
- `participant/requirements.txt`: minimal dependencies.

## Trusted package

- `evaluator/evaluate.py`: bounded, JSON-only artifact evaluator.
- `evaluator/README.md`: invocation, isolation, symlink, and directory-boundary rules.
- `evaluator/hidden/independent.py`: independent full-Fock-space numerical oracle.
- `evaluator/hidden/constraints.json`: trusted copy of frozen thresholds.
- `evaluator/hidden/validate_oracle.py`: CCSD=FCI, derivative, Hessian, and positivity checks.
- `evaluator/hidden/audit.py`: numerical cross-checks and malformed/security regression audit.
- `evaluator/hidden/robustness.py`: small-neighborhood achievability audit.
- `evaluator/hidden/calibrate.py`: pre-freeze broad private calibration.
- `evaluator/hidden/refine.py`: pre-freeze constrained feasibility refinement.
- `evaluator/hidden/calibration_round1/`: private random-search evidence and candidates.
- `evaluator/hidden/calibration_refined/`: private verified witness, evaluations, path/robustness records.
- `baseline/`: baseline wrapper, artifact, search report, and official evaluation.
- `adversary/`: malformed cases and machine-readable audit results.
- `attempts/`: main-owned isolated fresh-attempt outputs.
- `champions/`: provenance-labeled champion records; no author witness is a fresh champion.
- `freeze.json`: participant file digests and target freeze.
- `READY_FOR_MAIN.md`: launch/isolation handoff.
- `status.json`: package state, achievability, scores, and audit summary.
- `README.md`: author-facing overview and commands.
- `FILES.md`: this file map.
