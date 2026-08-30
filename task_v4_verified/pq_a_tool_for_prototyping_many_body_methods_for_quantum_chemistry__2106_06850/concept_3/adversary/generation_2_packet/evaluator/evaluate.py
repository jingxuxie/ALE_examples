"""Organizer-only, isolated, data-only JSON evaluator."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


PRIVATE = Path(__file__).resolve().parent / "private"


def failure(reason, started):
    return {"core": 0.0, "worst_fidelity": 0.0, "pass": False, "reason": reason,
            "fidelity_threshold": 0.999999999, "cases": [],
            "runtime_seconds": time.perf_counter() - started}


def evaluate(submission_path):
    started = time.perf_counter()
    if submission_path is None:
        return failure("missing submission path", started)
    try:
        process = subprocess.run(
            [sys.executable, "-I", str(PRIVATE / "judge.py"), os.path.abspath(submission_path)],
            cwd=PRIVATE, env={"PATH": os.defpath, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
            capture_output=True, text=True, timeout=20, check=False,
        )
        if process.returncode != 0:
            return failure("trusted checker failed or exceeded resource limit", started)
        report = json.loads(process.stdout)
        if type(report) is not dict or type(report.get("pass")) is not bool:
            return failure("invalid trusted-checker report", started)
        report["checker_runtime_seconds"] = report["runtime_seconds"]
        report["runtime_seconds"] = time.perf_counter() - started
        return report
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return failure("evaluation unavailable or timed out", started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission_path", nargs="?")
    parser.add_argument("--submission")
    parser.add_argument("--output", "--report", dest="output")
    arguments = parser.parse_args()
    if arguments.submission and arguments.submission_path:
        report = failure("supply only one submission path", time.perf_counter())
    else:
        report = evaluate(arguments.submission or arguments.submission_path)
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        destination = Path(arguments.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
