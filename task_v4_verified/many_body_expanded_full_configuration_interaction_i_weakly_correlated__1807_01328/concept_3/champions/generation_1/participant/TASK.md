# Predict the missing virtual-orbital correlation tail

**Mission.** Infer the signed, fourth-and-higher-order virtual-orbital MBE correlation-energy tail from CAS results through third order and affordable descriptors. These are simulated weakly correlated, pair-conserving Hamiltonians—not ab initio molecules or unrestricted electronic FCI.

**Assets.** `input/workspace/data/` contains 1,280 labeled training cases, 384 labeled validation cases, and 288 fixed unlabeled test cases. Two of six test families have no supplied labels. Model/distribution documentation, an independent synthetic generator, and a validation-selected tree/boosting/ridge baseline are provided in `input/workspace/`.

**Interface.** Submit `predictions.npz` with exactly `ids: U32[288]` and `tail: float[288]`. Match every test ID once; order is arbitrary. Predict the signed tail in synthetic Eh, not the total energy. Evaluation reads arrays only and never executes your code. See `SCHEMA.md` for the full contract.

**Baseline.** From `input/workspace`, run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B baseline/predict.py --output /path/to/writable/output/predictions.npz --report /path/to/writable/output/baseline_report.json`. The top-level `baseline/run.py` wrapper provides the same baseline; see its README.

**Objective.** Test RMSE ≤ 3e-5 synthetic Eh and worst-family RMSE ≤ 6e-5, with at least 35% and 25% improvement over the frozen baseline, respectively. All four conditions apply. Exact effective limits are in `data/baseline_reference.json`.

**Resources.** NumPy, SciPy, and scikit-learn are installed; no downloads. You have a one-hour construction window. There is no hidden-score API during construction. Static evaluation does not attest offline CPU or RAM usage. Independent synthetic training examples are allowed. Private labels, seeds and evaluator files are off limits. No known passing solution is supplied; this may remain open.
