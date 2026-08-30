import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
import time


G2ROOT = Path(__file__).resolve().parents[1]
AUTHORING = G2ROOT.parents[2] / "authoring"
if not (AUTHORING / "sandbox.py").is_file():
    raise RuntimeError(f"shared sandbox not found at {AUTHORING}")
sys.path.insert(0, str(AUTHORING))
from sandbox import run_python

specification = importlib.util.spec_from_file_location("g2_exact_routing", G2ROOT / "evaluator/routing.py")
routing = importlib.util.module_from_spec(specification)
specification.loader.exec_module(routing)
validate = routing.validate


def reject_constants(value):
    raise ValueError("non-finite JSON number: " + value)


def summarize(records, manifest, wall_seconds):
    valid = bool(records) and all(record["valid"] for record in records)
    family_scores = {}
    for family in sorted({record["family"] for record in records}):
        selected = [record for record in records if record["family"] == family]
        family_scores[family] = 1 - math.exp(sum(math.log(record["ratio"]) for record in selected) / len(selected)) if all(record["valid"] for record in selected) else -1.0
    core = 1 - math.exp(sum(math.log(record["ratio"]) for record in records) / len(records)) if valid else -1.0
    worst = min(family_scores.values(), default=-1.0)
    elapsed = sum(record.get("seconds", 0.0) for record in records)
    resources = elapsed <= manifest["suite_seconds"] and all(record.get("seconds", math.inf) <= manifest["case_seconds"] for record in records)
    reasons = []
    if not valid:
        reasons.append("one or more invalid or missing routes")
    if not resources:
        reasons.append("resource limit exceeded; do not treat timing jitter as quality hardness")
    if core < manifest["core_target"]:
        reasons.append("core quality below fixed target")
    if worst < manifest["worst_family_target"]:
        reasons.append("family quality below fixed target")
    return {"generation": 2, "valid": valid, "valid_cases": sum(record["valid"] for record in records),
            "case_count": len(records), "core_score": core, "worst_family_score": worst,
            "family_scores": family_scores, "resources_passed": resources,
            "runtime_seconds": elapsed, "evaluator_wall_seconds": wall_seconds,
            "core_target": manifest["core_target"], "worst_family_target": manifest["worst_family_target"],
            "case_seconds": manifest["case_seconds"], "suite_seconds": manifest["suite_seconds"],
            "resource_score": min(1.0, manifest["suite_seconds"] / max(elapsed, 1e-9)) if resources else 0.0,
            "passed": valid and resources and core >= manifest["core_target"] and worst >= manifest["worst_family_target"],
            "reason": "; ".join(reasons) or "all fixed targets met", "cases": records}


def evaluate(submission, cases_file=None, progress=None):
    started = time.monotonic()
    manifest = json.loads((G2ROOT / "evaluator/hidden/manifest.json").read_text())
    cases = json.loads(Path(cases_file or G2ROOT / "evaluator/hidden/cases.json").read_text())
    records = []
    for case in cases:
        record = {"id": case["id"], "family": case["family"], "valid": False}
        try:
            execution = run_python(submission, "solve.py", case, manifest["case_seconds"], memory_mb=manifest["memory_mb"])
            record.update(seconds=execution["seconds"], returncode=execution["returncode"], timed_out=execution["timed_out"])
            if execution["returncode"] != 0 or execution["timed_out"]:
                raise ValueError("execution failure: " + execution["stderr"][-1000:])
            answer = json.loads(execution["stdout"], parse_constant=reject_constants)
            record.update(validate(case, answer))
            record["baseline_cost"] = manifest["baseline"][case["id"]]["cost"]
            record["ratio"] = record["cost"] / record["baseline_cost"]
        except Exception as error:
            record["reason"] = str(error)
        records.append(record)
        if progress:
            Path(progress).write_text(json.dumps(summarize(records, manifest, time.monotonic() - started), indent=2) + "\n")
        print(json.dumps({key: record.get(key) for key in ("id", "valid", "ratio", "seconds", "reason")}), file=sys.stderr, flush=True)
    return summarize(records, manifest, time.monotonic() - started)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--output")
    parser.add_argument("--cases")
    parser.add_argument("--progress")
    arguments = parser.parse_args()
    result = evaluate(arguments.submission, arguments.cases, arguments.progress)
    text = json.dumps(result, indent=2)
    if arguments.output:
        Path(arguments.output).write_text(text + "\n")
    print(text)
