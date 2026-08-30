import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from run_attempt import inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    parser.add_argument("--attempt", default="v_1")
    parser.add_argument("--mode", choices=["A", "B", "E"], required=True)
    args = parser.parse_args()
    concept = args.concept.resolve()
    attempts = concept / "attempts"
    submission = attempts / args.attempt
    launch_path = attempts / (args.attempt + "_logs") / "launch.json"
    while True:
        try:
            launch = json.loads(launch_path.read_text())
        except (OSError, ValueError):
            time.sleep(5)
            continue
        if "finished" in launch:
            break
        time.sleep(5)
    current = inventory(submission)
    if current != launch["submission_sha256"]:
        raise RuntimeError("Submission changed after fresh-session completion; audit required")
    frozen = attempts / (args.attempt + "_frozen_submission")
    shutil.copytree(submission, frozen, symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".git", ".agents", ".codex"))
    report = attempts / (args.attempt + "_result.json")
    environment = dict(os.environ)
    environment.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       PYTHONDONTWRITEBYTECODE="1")
    evaluator = concept / "evaluator" / "evaluate.py"
    if args.mode == "A":
        command = ["/usr/bin/python3", str(evaluator), "--submission", str(frozen / "submission.py"),
                   "--report", str(report)]
    elif args.mode == "B":
        command = ["/usr/bin/python3", "-B", str(evaluator), str(frozen / "witness.json"),
                   "--output", str(report)]
    else:
        execution_copy = attempts / (args.attempt + "_evaluation_copy")
        shutil.copytree(frozen, execution_copy, symlinks=True)
        command = ["/usr/bin/python3", str(evaluator), "--submission", str(execution_copy),
                   "--output", str(report), "--", "/usr/bin/python3", "/submission/solution.py"]
    started = time.monotonic()
    with (attempts / (args.attempt + "_evaluation.log")).open("wb") as output:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=output,
                                stderr=subprocess.STDOUT, env=environment)
    audit = {"source_attempt": args.attempt, "fresh_exit_code": launch["returncode"],
             "fresh_elapsed_seconds": launch["elapsed_seconds"], "mode": args.mode,
             "original_unchanged_before_evaluation": True,
             "original_unchanged_after_evaluation": inventory(submission) == current,
             "frozen_submission_sha256": inventory(frozen), "evaluator_command": command,
             "evaluation_returncode": result.returncode,
             "evaluation_wall_seconds": time.monotonic() - started}
    (attempts / (args.attempt + "_evaluation_audit.json")).write_text(json.dumps(audit, indent=2) + "\n")
    if not report.is_file():
        raise RuntimeError("Evaluator did not emit a report; inspect execution log")
    metrics = json.loads(report.read_text())
    print(json.dumps({key: metrics[key] for key in (
        "valid", "passed", "core_score", "worst_family_score", "runtime_score", "reason",
        "pooled", "execution", "mean_family_log_rmse", "worst_regime_family_log_rmse"
    ) if key in metrics}, indent=2), flush=True)


if __name__ == "__main__":
    main()
