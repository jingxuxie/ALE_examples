import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import risks


def main():
    spec = importlib.util.spec_from_file_location("private_evaluator", ROOT / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    baseline_path = ROOT / "participant/baseline/design.json"
    baseline = json.loads(baseline_path.read_text())
    checks = {}
    baseline_score = evaluator.evaluate(baseline_path)
    checks["baseline_legal"] = baseline_score["valid"] and not baseline_score["passed"]
    checks["baseline_zero_score"] = abs(baseline_score["core_score"]) < 1e-10
    checks["missing_file_rejected"] = not evaluator.evaluate(ROOT / "adversary/no-such-file.json")["valid"]
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temp:
        temp = Path(temp)
        variants = {
            "empty": {"batches": []},
            "boolean": {"batches": [True] * len(baseline["batches"])},
            "negative": {"batches": [-1] * len(baseline["batches"])},
            "floating": {"batches": [float(value) for value in baseline["batches"]]},
            "overspend": {"batches": [48] * len(baseline["batches"])},
            "empty_design": {"batches": [0] * len(baseline["batches"])},
            "extra_key": dict(baseline, score=1),
            "oversized_integer": {"batches": [10 ** 100] * len(baseline["batches"])},
        }
        for name, value in variants.items():
            path = temp / (name + ".json")
            path.write_text(json.dumps(value))
            checks[name + "_rejected"] = not evaluator.evaluate(path)["valid"]
        environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
        generated = temp / "rerun.json"
        subprocess.run([sys.executable, str(ROOT / "participant/baseline/solve.py"), "--output", str(generated)],
                       check=True, env=environment, stdout=subprocess.PIPE, text=True)
        checks["baseline_reproducible"] = json.loads(generated.read_text()) == baseline
    data = np.load(ROOT / "evaluator/hidden/benchmark.npz")
    reference_risks = risks(data["features"], np.array(baseline["batches"]))
    checks["independent_information_assembly"] = abs(reference_risks.mean() - baseline_score["mean_risk"]) < 1e-9
    development = np.load(ROOT / "participant/input/development.npz")
    checks["heldout_parameters_disjoint"] = all(not np.any(np.all(development["parameters"] == row, axis=1))
                                                for row in data["parameters"])
    simulator = json.loads((ROOT / "adversary/results/build_audit.json").read_text())
    checks["density_matrix_and_derivative_audit"] = simulator["simulator_valid"]
    checks = {name: bool(value) for name, value in checks.items()}
    result = dict(passed=all(checks.values()), checks=checks, baseline_score=baseline_score)
    (ROOT / "adversary/results/evaluator_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
