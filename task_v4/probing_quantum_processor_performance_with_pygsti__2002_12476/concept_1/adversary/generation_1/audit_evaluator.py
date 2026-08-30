import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    evaluator = module(ROOT / "evaluator/evaluate.py", "current_loss_evaluator")
    independent = module(ROOT / "adversary/portfolio/resilience/metrics.py", "independent_woodbury")
    baseline_path = ROOT / "participant/baseline/design.json"
    baseline = json.loads(baseline_path.read_text())
    counts = np.array(baseline["batches"])
    checks = {}
    result = evaluator.evaluate(baseline_path)
    checks["baseline_valid_not_passing"] = result["valid"] and not result["passed"]
    checks["baseline_zero_reduction"] = abs(result["core_score"]) < 1e-9 and abs(result["worst_family_score"]) < 1e-9
    checks["baseline_intact_ratio_one"] = abs(result["intact_mean_ratio"] - 1) < 1e-9
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
        directory = Path(temporary)
        malformed = {
            "zero": {"batches": [0] * len(counts)},
            "wrong_length": {"batches": [1]},
            "booleans": {"batches": [True] * len(counts)},
            "floats": {"batches": [float(value) for value in counts]},
            "negative": {"batches": [-1] * len(counts)},
            "overspend": {"batches": [48] * len(counts)},
            "extra_key": dict(baseline, passed=True),
            "huge_integer": {"batches": [10 ** 100] * len(counts)},
        }
        for name, value in malformed.items():
            path = directory / (name + ".json")
            path.write_text(json.dumps(value))
            checks[name + "_rejected"] = not evaluator.evaluate(path)["valid"]
        symlink = directory / "linked.json"
        symlink.symlink_to(baseline_path)
        checks["symlink_rejected"] = not evaluator.evaluate(symlink)["valid"]
        path = directory / "duplicate.json"
        path.write_text('{"batches":[],"batches":' + json.dumps(baseline["batches"]) + '}')
        checks["duplicate_key_rejected"] = not evaluator.evaluate(path)["valid"]
        path = directory / "nonfinite.json"
        path.write_text('{"batches":[NaN]}')
        checks["nonfinite_json_rejected"] = not evaluator.evaluate(path)["valid"]
        checks["missing_file_rejected"] = not evaluator.evaluate(directory / "missing.json")["valid"]
        degenerate = np.zeros(len(counts), dtype=int)
        degenerate[0] = 1
        path = directory / "degenerate.json"
        path.write_text(json.dumps({"batches": degenerate.tolist()}))
        score = evaluator.evaluate(path)
        checks["fewer_than_two_circuits_lose_all_information"] = score["valid"] and not score["passed"] and score["mean_loss_risk"] > 1e10
        path = directory / "reproduced.json"
        subprocess.run([sys.executable, str(ROOT / "participant/baseline/solve.py"), "--output", str(path)], check=True)
        checks["baseline_runnable_and_reproducible"] = path.read_bytes() == baseline_path.read_bytes()
    with np.load(ROOT / "evaluator/hidden/benchmark.npz", allow_pickle=False) as data:
        selected = data["features"][:6]
        intact, loss, pairs = evaluator.risk_profile(selected, counts, 2, 64)
        reference = independent.profile(selected, counts, direct=False)
        error = float(np.max(np.abs(loss - reference["double"]) / loss))
        checks["independent_rank_two_identity_agrees"] = error < 1e-5
        checks["stored_baseline_loss_matches"] = np.allclose(loss, data["champion_loss_risks"][:6], rtol=1e-10)
        checks["loss_dominates_intact_risk"] = np.all(loss >= intact)
        checks["every_selected_pair_considered"] = all(len(pair) == 2 for pair in pairs)
    archive = ROOT / "generations/generation_0/participant/workspace/physics.py"
    checks["physical_forward_model_unchanged"] = archive.read_bytes() == (ROOT / "participant/workspace/physics.py").read_bytes()
    checks = {name: bool(value) for name, value in checks.items()}
    audit = dict(passed=all(checks.values()), checks=checks, independent_rank_two_relative_error=error,
                 baseline_score=result, targets_frozen_before_challenger=True,
                 original_density_matrix_audit="../../generations/generation_0/adversary/results/build_audit.json")
    (Path(__file__).parent / "evaluator_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(dict(passed=audit["passed"], checks=checks, independent_rank_two_relative_error=error), indent=2))
    if not audit["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
