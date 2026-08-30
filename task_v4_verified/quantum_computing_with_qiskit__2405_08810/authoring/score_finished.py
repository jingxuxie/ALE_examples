import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int, choices=[1, 2, 3])
    parser.add_argument("--generation", type=int, default=1)
    arguments = parser.parse_args()
    concept = ROOT / f"concept_{arguments.concept}"
    run_file = concept / "adversary" / "tournament" / f"v_{arguments.generation}" / "run.json"
    deadline = time.monotonic() + 3720
    while time.monotonic() < deadline:
        try:
            record = json.loads(run_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            record = {}
        if "returncode" in record:
            break
        time.sleep(5)
    else:
        raise TimeoutError("fresh-run completion record not available")
    if not record.get("participant_unchanged"):
        raise ValueError("participant assets changed during the attempt")
    destination = concept / "adversary" / "scored" / f"v_{arguments.generation}"
    destination.mkdir(parents=True, exist_ok=False)
    snapshot = destination / "submission"
    shutil.copytree(concept / "attempts" / f"v_{arguments.generation}", snapshot, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", ".agents", ".codex", "__pycache__"))
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    temporary = tempfile.TemporaryDirectory(prefix="calibration_submission_") if arguments.concept == 3 else None
    evaluation_submission = snapshot
    if temporary is not None:
        evaluation_submission = Path(temporary.name) / "submission"
        shutil.copytree(snapshot, evaluation_submission, symlinks=True)
    command = ["/usr/bin/python3", str(concept / "evaluator" / "evaluate.py"), str(evaluation_submission), "--output", str(destination / "score.json")]
    try:
        with (destination / "stdout.log").open("w") as stdout, (destination / "stderr.log").open("w") as stderr:
            result = subprocess.run(command, env=environment, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=1800)
    finally:
        if temporary is not None:
            temporary.cleanup()
    report = json.loads((destination / "score.json").read_text())
    print(json.dumps({"concept": arguments.concept, "generation": arguments.generation, "evaluator_exit": result.returncode, "core_score": report.get("core_score"), "worst_family_score": report.get("worst_family_score"), "passed": report.get("passed"), "valid": report.get("valid"), "reason": report.get("reason")}), flush=True)
    if arguments.concept == 1 and report.get("passed"):
        champion = concept / "champions" / f"generation_{arguments.generation}"
        shutil.copytree(snapshot, champion, symlinks=True)
        shutil.copy2(destination / "score.json", champion.parent / f"generation_{arguments.generation}_score.json")
        if arguments.generation != 1:
            return
        stress_file = concept / "adversary" / "private_stress" / "cases.json"
        stress_command = command[:3] + ["--cases", str(stress_file), "--output", str(destination / "stress_score.json")]
        with (destination / "stress_stdout.log").open("w") as stdout, (destination / "stress_stderr.log").open("w") as stderr:
            subprocess.run(stress_command, env=environment, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=1800)
        print("champion private stress scoring complete", flush=True)


if __name__ == "__main__":
    main()
