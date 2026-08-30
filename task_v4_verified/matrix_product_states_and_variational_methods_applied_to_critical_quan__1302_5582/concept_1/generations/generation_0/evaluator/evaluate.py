"""Frozen private evaluator; participant execution is always delegated to bwrap."""

import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

from trusted_contractor import load_mps, measure
from sandbox_runner import SandboxUnavailable, run_submission
from hidden.suite import cases


ROOT = Path(__file__).resolve().parent.parent


def quality(energy, baseline, reference, length):
    gap = max(baseline - reference, 1e-7 * length)
    regret = max(0.0, (energy - reference) / gap)
    return max(0.0, min(1.0, -math.log10(max(regret, 1e-4)) / 4))


def aggregate(rows, scoring):
    families = {}
    values = []
    runtimes = []
    all_valid = True
    minimum_long = 1.0
    for row in rows:
        short = row["stages"]["short"]
        long = row["stages"]["long"]
        core = 0.75 * long["quality"] + 0.25 * short["quality"]
        families.setdefault(row["family"], []).append(core)
        values.append(core)
        runtimes.append(long["quality"] * max(0.0, 1 - long["cpu_seconds"] / 40))
        all_valid = all_valid and short["valid"] and long["valid"]
        minimum_long = min(minimum_long, long["quality"])
    family_scores = {family: sum(entries) / len(entries) for family, entries in families.items()}
    core = sum(values) / len(values)
    worst = min(family_scores.values())
    runtime = sum(runtimes) / len(runtimes)
    score = 100 * (0.70 * core + 0.25 * worst + 0.05 * runtime)
    target = scoring["target"]
    passed = all_valid and score >= target["score_min"] and core >= target["core_min"] and worst >= target["worst_family_min"] and minimum_long >= target["each_long_quality_min"]
    reason = "quality, worst-family and resource targets satisfied" if passed else (
        "one or more outputs invalid or exceeded resource limits" if not all_valid
        else "fixed improvement target not met")
    return {"score": score, "core": core, "worst_family": worst, "runtime": runtime,
            "core_score": core, "worst_family_score": worst, "resource_score": runtime,
            "passed": passed, "valid": all_valid, "reason": reason,
            "family_scores": family_scores, "minimum_long_quality": minimum_long,
            "all_valid": all_valid,
            "target_met": passed}


def evaluate(submission, output):
    scoring = json.loads((ROOT / "participant/input/scoring.json").read_text())
    calibration_path = ROOT / "evaluator/hidden/calibration.json"
    calibration = json.loads(calibration_path.read_text())
    for relative, expected in calibration["frozen_hashes"].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError("frozen asset hash mismatch: " + relative)
    submission = Path(submission).resolve()
    if not (submission / "solve.py").is_file():
        raise ValueError("submission must contain solve.py")
    files = list(submission.rglob("*"))
    if any(path.is_symlink() for path in files):
        raise ValueError("submission symlinks are not allowed")
    if sum(path.stat().st_size for path in files if path.is_file()) > scoring["submission_bytes_max"]:
        raise ValueError("submission exceeds 16 MiB")
    rows = []
    with tempfile.TemporaryDirectory(prefix=".evaluation-", dir=Path(output).resolve().parent) as temporary:
        temporary = Path(temporary)
        for family, base_request in cases():
            row = {"case_id": base_request["case_id"], "family": family, "stages": {}}
            reference = calibration["cases"][base_request["case_id"]]
            for stage, budget in scoring["stages"].items():
                request = dict(base_request, budget_seconds=budget["cpu_seconds"],
                               wall_seconds=budget["wall_seconds"])
                location = temporary / (base_request["case_id"] + "-" + stage)
                copied = location / "submission"
                shutil.copytree(submission, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                result = run_submission(copied, ROOT / "participant", location / "scratch", request)
                stage_result = {key: value for key, value in result.items() if key != "state_path"}
                stage_result.update(valid=False, quality=0.0)
                if result["process_valid"]:
                    try:
                        measured = measure(load_mps(result["state_path"], request), request)
                        stage_result.update(measured)
                        stage_result["valid"] = True
                        stage_result["quality"] = quality(measured["energy"],
                            reference["baseline"][stage]["energy"], reference["reference"]["energy"],
                            request["n_sites"])
                    except Exception as error:
                        stage_result["error"] = type(error).__name__ + ": " + str(error)
                row["stages"][stage] = stage_result
            rows.append(row)
    return {"version": 1, "benchmark": "finite-phi4-mps-v1", "cases": rows,
            "summary": aggregate(rows, scoring),
            "calibration_sha256": hashlib.sha256(calibration_path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = evaluate(args.submission, output)
    except SandboxUnavailable as error:
        output.write_text(json.dumps({"status": "infrastructure_error", "error": str(error),
                                      "score": None, "fail_closed": True}, indent=2))
        print("Sandbox unavailable; evaluation aborted without fallback", file=sys.stderr)
        return 2
    except Exception as error:
        output.write_text(json.dumps({"status": "evaluation_error", "error": str(error)}, indent=2))
        return 2
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
