import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

from evaluate import read_hidden, score, validate_predictions


def main():
    report = {"syntax_files": 0, "scorer_rejections": 0, "split_counts": {}, "checks": []}
    for path in ROOT.rglob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
        report["syntax_files"] += 1
    manifest = json.loads((ROOT / "hidden/manifest.json").read_text())
    seen = set()
    for name, relative in (("train", "participant/input/train.jsonl"),
                           ("validation", "participant/input/validation.jsonl"),
                           ("test", "hidden/test.jsonl")):
        path = ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["splits"][name]["sha256"]
        records = [json.loads(line) for line in path.read_text().splitlines()]
        report["split_counts"][name] = len(records)
        counts = Counter((case["L"], case["family"]) for case in records)
        assert len(counts) == 8 and len(set(counts.values())) == 1
        for case in records:
            fields = case["fields"]
            assert case["L"] in (10, 12) and len(fields) == case["L"]
            assert all(math.isfinite(field) for field in fields)
            assert min(right - left for left, right in zip(sorted(fields), sorted(fields)[1:])) > 1e-8
            assert math.isfinite(case["f"]) and 0 <= case["f"] <= 1
            signature = tuple(fields)
            assert signature not in seen
            seen.add(signature)
    assert len(read_hidden()) == 320
    assert (ROOT / "participant/workspace/physics.py").read_bytes() == (ROOT / "evaluator/physics.py").read_bytes()
    assert (ROOT / "participant/TASK.md").read_bytes() == (ROOT / "TASK.md").read_bytes()
    targets = json.loads((ROOT / "evaluator/targets.json").read_text())
    assert targets["frozen"] and targets["overall_rmse"] == 0.035 and targets["worst_family_rmse"] == 0.05
    assert targets["wall_seconds"] == 3 and targets["startup_seconds"] == 60
    cases = [{"id": "first", "L": 10, "family": "iid_uniform", "f": 0.2},
             {"id": "second", "L": 12, "family": "ordered_blocks", "f": 0.8}]
    valid = {"predictions": [{"id": "second", "f": 0.8}, {"id": "first", "f": 0.2}]}
    predictions = validate_predictions(valid, cases)
    assert score(cases, predictions, targets)["passed"]
    invalid = [[], {}, {"predictions": []}, {"predictions": valid["predictions"], "extra": 1},
               {"predictions": [{"id": "first", "f": 0.2}] * 2},
               {"predictions": [{"id": "unknown", "f": 0.2}, {"id": "second", "f": 0.8}]}]
    for estimate in (float("nan"), float("inf"), True, "0.2", None, -0.01, 1.01):
        invalid.append({"predictions": [{"id": "first", "f": estimate}, {"id": "second", "f": 0.8}]})
    for payload in invalid:
        try:
            validate_predictions(payload, cases)
        except ValueError:
            report["scorer_rejections"] += 1
        else:
            raise AssertionError("Invalid prediction accepted")
    benchmark = json.loads((ROOT / "participant/input/official_streaming_benchmark.json").read_text())
    assert benchmark["all_within_limits"] and benchmark["runs"]
    for run in benchmark["runs"]:
        assert run["official_isolated_evaluation"]
        assert run["resources"]["wall_seconds"] < 3
        assert run["resources"]["startup_seconds"] < 60
        assert run["resources"]["cpu_affinity_expansion"] == "seccomp denied"
    report["official_validation_runs"] = len(benchmark["runs"])
    report["checks"] = ["hash-verified frozen datasets", "balanced independent field records",
                         "finite nondegenerate fields and bounded targets", "identical frozen physics copies",
                         "identical participant task specification", "fixed targets and final resource limits",
                         "strict prediction contract", "official streaming benchmark passed"]
    report["public_artifact_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "participant").rglob("*")) if path.is_file()}
    report["evaluator_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "evaluator").glob("*")) if path.is_file()}
    (ROOT / "authoring/package_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if "sha256" not in key}, indent=2))


if __name__ == "__main__":
    main()
