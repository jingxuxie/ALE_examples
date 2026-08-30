import argparse
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from contract import validate


def run_submission(submission, case, timeout):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="pq_plan_eval_") as temporary:
        work = Path(temporary)
        (work / "input.json").write_text(json.dumps(case))
        command = ["bwrap", "--die-with-parent", "--new-session", "--unshare-all",
                   "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
                   "--ro-bind", "/lib64", "/lib64", "--dev", "/dev", "--proc", "/proc",
                   "--tmpfs", "/tmp", "--ro-bind", str(submission), "/submission",
                   "--ro-bind", str(ROOT / "participant"), "/participant",
                   "--ro-bind", str(ROOT / "participant"), str(ROOT / "participant"),
                   "--ro-bind", str(ROOT / "evaluator/executor.py"), "/trusted_executor.py",
                   "--bind", str(work), "/work", "--chdir", "/work",
                   "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
                   "--setenv", "PYTHONPATH", "/participant/workspace",
                   "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "1",
                   "--setenv", "MKL_NUM_THREADS", "1", "/usr/bin/python3", "/trusted_executor.py"]
        try:
            with (work / "stdout.txt").open("w") as stdout, (work / "stderr.txt").open("w") as stderr:
                process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                         timeout=timeout + 240)
            if process.returncode:
                raise RuntimeError("sandbox infrastructure exit " + str(process.returncode) + ": " + (work / "stderr.txt").read_text()[-2000:])
            execution = json.loads((work / "stdout.txt").read_text())
            if execution["returncode"]:
                raise ValueError("planner timeout" if execution["timed_out"] else "planner exit: " + execution["stderr"])
            target = work / "output.json"
            if target.is_symlink() or not target.is_file() or target.stat().st_size > 16 * 1024**2:
                raise ValueError("missing or oversized output")
            plan = json.loads(target.read_text())
            result = validate(case, plan)
            result["reason"] = "exact tensor-network equality and memory constraints verified"
            result["planner_seconds"] = execution["planner_seconds"]
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            result = {"valid": False, "infrastructure_error": True, "reason": str(error)}
        except Exception as error:
            result = {"valid": False, "reason": str(error)}
    result["wall_seconds"] = time.monotonic() - started
    return result


def evaluate(submission, public=False):
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    specification = importlib.util.spec_from_file_location("trusted_baseline", ROOT / "participant/baseline/solve.py")
    baseline = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(baseline)
    records = []
    entries = manifest["cases"]
    if public:
        entries = [{"file": str(path), "family": path.stem,
                    "baseline": json.loads(path.with_name(path.stem + ".baseline.json").read_text())}
                   for path in sorted((ROOT / "participant/input").glob("*.json")) if ".baseline." not in path.name]
    for entry in entries:
        path = Path(entry["file"]) if public else ROOT / "evaluator/hidden" / entry["file"]
        case = json.loads(path.read_text())
        baseline_metric = validate(case, baseline.solve(case))
        if baseline_metric["flops"] != entry["baseline"]["flops"]:
            raise ValueError("stored baseline does not match trusted recomputation")
        result = run_submission(submission, case, manifest["planner_timeout_seconds"])
        result["case"] = path.name
        result["family"] = entry["family"]
        result["baseline_flops"] = entry["baseline"]["flops"]
        result["speedup"] = result["baseline_flops"] / max(1, result["flops"]) if result["valid"] else 0
        records.append(result)
        print(json.dumps({"case": path.name, "valid": result["valid"], "speedup": result["speedup"],
                          "wall_seconds": result["wall_seconds"], "reason": result["reason"]}), file=sys.stderr, flush=True)
    grouped = defaultdict(list)
    for result in records:
        grouped[result["family"]].append(result["speedup"])

    def geomean(values):
        return math.exp(sum(math.log(value) for value in values) / len(values)) if values and min(values) > 0 else 0

    families = {family: geomean(values) for family, values in grouped.items()}
    core = geomean([record["speedup"] for record in records])
    worst = min(families.values(), default=0)
    valid = all(record["valid"] for record in records) and bool(records)
    passed = valid and core >= manifest["target_geomean_speedup"] and worst >= manifest["target_worst_family_speedup"]
    return {"core_score": core, "worst_family_score": worst, "family_scores": families,
            "runtime_seconds": sum(record.get("planner_seconds", 30) for record in records),
            "sandbox_wall_seconds": sum(record["wall_seconds"] for record in records),
            "infrastructure_valid": not any(record.get("infrastructure_error") for record in records),
            "resource_score": min((record.get("resource_score", 0) for record in records), default=0),
            "valid": valid, "passed": passed,
            "reason": "fixed improvement targets met" if passed else "invalid plan or fixed improvement targets not met",
            "cases": records, "targets": {key: manifest[key] for key in manifest if key.startswith("target_")}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--public", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate(args.submission.resolve(), args.public)
    except Exception as error:
        result = {"core_score": 0, "worst_family_score": 0, "passed": False, "valid": False, "reason": str(error)}
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.report:
        args.report.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
