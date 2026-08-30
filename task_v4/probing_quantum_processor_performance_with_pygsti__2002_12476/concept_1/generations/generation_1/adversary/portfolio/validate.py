import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import fisher_features, risks, validate_batches


def main():
    candidates = json.loads((ROOT / "participant/input/candidates.json").read_text())
    contract = json.loads((ROOT / "participant/input/contract.json").read_text())
    submitted = json.loads((HERE / "design.json").read_text())
    counts, cost = validate_batches(submitted["batches"], candidates, contract)
    data = np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False)
    features = data["features"]
    support = np.flatnonzero(counts)
    selected = features[:, support]
    computed_risks = risks(features, counts)
    information = selected.transpose(0, 2, 1) @ (selected * (64 * counts[support])[None, :, None])
    covariance = np.linalg.inv(information + np.eye(14)[None] * 1e-10)
    projection = selected @ covariance[:, :, :12]
    analytic = -64 * np.mean(np.sum(projection * projection, axis=2), axis=0) / data["baseline_risks"].mean()
    finite = []
    step = 0.001
    for index in support:
        plus, minus = counts.astype(float), counts.astype(float)
        plus[index] += step
        minus[index] -= step
        finite.append((risks(features, plus).mean() - risks(features, minus).mean()) /
                      (2 * step * data["baseline_risks"].mean()))
    finite = np.array(finite)
    model_errors = []
    selected_candidates = [candidates[index] for index in support]
    for family in np.unique(data["families"]):
        scenario = int(np.flatnonzero(data["families"] == family)[0])
        rebuilt = fisher_features(data["parameters"][scenario], selected_candidates)
        model_errors.append(float(np.max(np.abs(rebuilt - selected[scenario]))))
    spec = importlib.util.spec_from_file_location("private_validation_evaluator", ROOT / "evaluator/evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evaluated = module.evaluate(HERE / "design.json")
    baseline = np.array(json.loads((ROOT / "participant/baseline/design.json").read_text())["batches"])
    baseline_error = float(np.max(np.abs(risks(features, baseline) - data["baseline_risks"])))
    gradient_error = np.max(np.abs(finite - analytic))
    risk_error = abs(float(computed_risks.mean()) - evaluated["mean_risk"])
    hash_paths = ["participant/TASK.md", "participant/input/contract.json", "participant/input/candidates.json",
                  "participant/workspace/physics.py", "participant/baseline/design.json",
                  "evaluator/evaluate.py", "evaluator/hidden/contract.json", "evaluator/hidden/benchmark.npz"]
    result = dict(valid=True, execution_ticks=cost, distinct_circuits=int(len(support)),
                  total_batches=int(counts.sum()), total_shots=int(counts.sum() * 64), max_batches=int(counts.max()),
                  gradient_absolute_error=float(gradient_error),
                  gradient_relative_error=float(np.max(np.abs(finite - analytic) / np.maximum(np.abs(analytic), 1e-10))),
                  frozen_feature_recomputation_max_error=max(model_errors), evaluator_mean_risk_absolute_error=risk_error,
                  stored_baseline_risk_max_error=baseline_error,
                  design_sha256=hashlib.sha256((HERE / "design.json").read_bytes()).hexdigest(),
                  frozen_asset_sha256={path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in hash_paths},
                  evaluator_passed=evaluated["passed"], fresh_artifacts_read=False)
    result["checks_passed"] = bool(gradient_error < 1e-7 and risk_error < 1e-9 and
                                  baseline_error < 1e-9 and max(model_errors) < 1e-8 and evaluated["passed"])
    (HERE / "numerical_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
