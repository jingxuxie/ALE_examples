# Concept 3 — Mode D hidden pair-space tail prediction

**Privileged generator sidecar, not a fresh solver.** Expose only `participant/` to a fresh solver: copy `participant/input/workspace/` into its writable workspace, and supply `participant/TASK.md`. Keep `evaluator/`, `attempts/`, `champions/`, `adversary/`, and root status/README private. They contain labels, seeds or private artifacts. Never expose the parent task tree. No fresh agent is launched here.

The model is synthetic, not an ab initio claim. Paper auditing is outside this sidecar's scope. Test features are intentionally visible; the evaluator reads only a submitted NPZ and executes no participant code.

- Baseline: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B participant/input/workspace/baseline/predict.py --output attempts/baseline/predictions.npz --report attempts/baseline/training_report.json`.
- Seal once: `python -B evaluator/seal_release.py`.
- Evaluate: `python -B evaluator/evaluate.py /path/to/predictions.npz --output attempts/score.json`.
- Audit: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m unittest discover -s evaluator/tests -v`.

Criteria predate release generation and are hashed in `evaluator/hidden/generation_freeze.json`. The baseline had an import-only prelaunch compatibility amendment for installed experimental scikit-learn HGB; estimators, selection, data and targets are unchanged. The integrity manifest freezes labels, features, baseline, evaluator and public generator/code; prelaunch interface-only hash amendments are recorded separately. Integrity failures fail closed. Construction lasts one hour, with no hidden-score API. Static evaluation does not attest offline CPU/RAM usage. Historical resource-request metadata in the preserved criteria is not an enforced runner policy; the corrected participant mission supersedes that non-scoring guidance. Launch readiness and known-passing status are separate in `status.json`.

The required top-level `participant/workspace/` contains a pointer to the canonical nested workspace, and `participant/baseline/run.py` executes its unchanged baseline with writable prediction/report paths. `adversary/prelaunch_interface_amendments.json` records these interface amendments and verifies that scientific artifacts remain byte-identical.
