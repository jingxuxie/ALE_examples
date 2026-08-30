import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "authoring"))
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from sandbox import run_python
from routing import validate


def reject_constants(value):
    raise ValueError("non-finite JSON number: " + value)


def evaluate(submission, cases_file=None):
    manifest = json.loads((ROOT / "evaluator" / "hidden" / "manifest.json").read_text())
    cases = json.loads(Path(cases_file or ROOT / "evaluator" / "hidden" / "cases.json").read_text())
    baseline = manifest["baseline"]
    records = []
    started = time.monotonic()
    for case in cases:
        record = {"id": case["id"], "family": case["family"], "valid": False}
        try:
            execution = run_python(submission, "solve.py", case, manifest["case_seconds"])
            record["seconds"] = execution["seconds"]
            if execution["timed_out"] or execution["returncode"] != 0:
                raise ValueError("timeout or execution failure: " + execution["stderr"][-1000:])
            answer = json.loads(execution["stdout"], parse_constant=reject_constants)
            metrics = validate(case, answer)
            record.update(metrics)
            record["baseline_cost"] = baseline[case["id"]]["cost"]
            record["ratio"] = record["cost"] / record["baseline_cost"]
        except Exception as error:
            record["reason"] = str(error)
        records.append(record)
    elapsed = sum(record.get("seconds", 0) for record in records)
    valid = all(record["valid"] for record in records) and bool(records)
    family_scores = {}
    for family in sorted({case["family"] for case in cases}):
        selected = [record for record in records if record["family"] == family]
        family_scores[family] = 1 - math.exp(sum(math.log(record["ratio"]) for record in selected) / len(selected)) if all(record["valid"] for record in selected) else -1.0
    core = 1 - math.exp(sum(math.log(record["ratio"]) for record in records) / len(records)) if valid else -1.0
    worst = min(family_scores.values(), default=-1.0)
    resources = elapsed <= manifest["suite_seconds"] and all(record.get("seconds", math.inf) <= manifest["case_seconds"] for record in records)
    passed = valid and resources and core >= manifest["core_target"] and worst >= manifest["worst_family_target"]
    reasons = []
    if not valid:
        reasons.append("one or more illegal or missing routes")
    if not resources:
        reasons.append("resource limit exceeded")
    if core < manifest["core_target"]:
        reasons.append("aggregate improvement below fixed target")
    if worst < manifest["worst_family_target"]:
        reasons.append("worst-family improvement below fixed target")
    return {"core_score": core, "worst_family_score": worst, "family_scores": family_scores,
            "resource_score": min(1.0, manifest["suite_seconds"] / max(elapsed, 1e-9)) if resources else 0.0,
            "runtime_seconds": elapsed, "evaluator_wall_seconds": time.monotonic() - started,
            "valid": valid, "passed": passed, "reason": "; ".join(reasons) or "all fixed targets met", "cases": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--output")
    parser.add_argument("--cases")
    arguments = parser.parse_args()
    try:
        result = evaluate(arguments.submission, arguments.cases)
    except Exception as error:
        result = {"core_score": -1, "worst_family_score": -1, "resource_score": 0,
                  "valid": False, "passed": False, "reason": str(error)}
    text = json.dumps(result, indent=2)
    if arguments.output:
        Path(arguments.output).write_text(text + "\n")
    print(text)
