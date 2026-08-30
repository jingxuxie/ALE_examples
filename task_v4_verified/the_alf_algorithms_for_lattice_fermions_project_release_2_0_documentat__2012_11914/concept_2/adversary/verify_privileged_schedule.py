import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", default="adversary/topology_refine/submission.json")
    parser.add_argument("--score", default="adversary/privileged_generation2_confirmation.json")
    parser.add_argument("--output", default="adversary/privileged_schedule_high_precision.json")
    arguments = parser.parse_args()
    grader = load_module("design_grader", ROOT / "evaluator/evaluate.py")
    independent = load_module("independent_precision", ROOT / "adversary/verify_champion_failure.py")
    artifact = ROOT / arguments.submission
    official = json.loads((ROOT / arguments.score).read_text())
    assert official["valid"]
    rules = grader.contract()
    payload, artifact_bytes = grader.read_submission(artifact, rules)
    stages = grader.canonical_stages(payload["stages"])
    baseline = grader.canonical_stages(grader.reference_stages(rules))
    point = official["worst_point"]
    cases = json.loads((ROOT / "evaluator/hidden/instances.json").read_text())["instances"]
    instance = next(case for case in cases if case["id"] == point["case_id"])
    report = independent.verify(instance, stages, baseline, point["dtau"], point["repetitions"], 70)
    discrepancy = abs(float(report["ratios"][point["observable"]]) - point["ratio"])
    assert discrepancy < 1e-7
    result = {
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "artifact_bytes": artifact_bytes,
        "official_report": arguments.score,
        "official_pass_decision": official["passed"],
        "independent_method": "70-digit full matrices, Hermitian eigensystems, analytic bond exponentials, explicit repeated product",
        "certifies": "agreement at the official worst point, not a separate all-points high-precision score",
        "official_worst_point": point,
        "high_precision": report,
        "absolute_ratio_discrepancy": discrepancy,
        "passed": True
    }
    (ROOT / arguments.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
