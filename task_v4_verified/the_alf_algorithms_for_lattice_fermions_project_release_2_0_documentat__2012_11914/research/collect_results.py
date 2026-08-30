import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def collect(concept_name, generation):
    concept = ROOT / concept_name
    run_path = concept / "attempts" / "logs" / f"v_{generation}.run.json"
    if not run_path.exists():
        return None
    try:
        run = json.loads(run_path.read_text())
    except json.JSONDecodeError:
        return None
    if run["state"] != "finished":
        return None
    report_path = concept / "attempts" / f"v_{generation}.evaluation.json"
    if report_path.exists():
        return json.loads(report_path.read_text())
    if not run.get("participant_unchanged"):
        return {"passed": False, "valid": False, "evaluator_execution_error": "Participant changed during attempt; cannot infer scientific hardness"}
    submission = concept / "attempts" / f"v_{generation}"
    if concept_name == "concept_2":
        submission = submission / "submission.json"
    command = [sys.executable, str(concept / "evaluator" / "evaluate.py"), "--submission", str(submission), "--output", str(report_path)]
    environment = dict(os.environ)
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    log_path = concept / "attempts" / "logs" / f"v_{generation}.evaluation.log"
    try:
        with log_path.open("w") as log:
            result = subprocess.run(command, cwd=concept, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, timeout=300, env=environment)
        if result.returncode != 0 or not report_path.exists():
            return {"passed": False, "valid": False, "evaluator_execution_error": f"Checker exit {result.returncode}; see {log_path}"}
        return json.loads(report_path.read_text())
    except Exception as error:
        return {"passed": False, "valid": False, "evaluator_execution_error": str(error)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--jobs", nargs="+", default=["concept_1:2", "concept_2:1", "concept_3:1"])
    parser.add_argument("--output", type=Path, default=ROOT / "research" / "tournament_results.json")
    arguments = parser.parse_args()
    jobs = {entry.split(":")[0]: int(entry.split(":")[1]) for entry in arguments.jobs}
    completed = {}
    while True:
        for concept, generation in jobs.items():
            if concept in completed:
                continue
            report = collect(concept, generation)
            if report is not None:
                completed[concept] = {"generation": generation, "evaluation": report}
                print(json.dumps({"concept": concept, "generation": generation, "core_score": report.get("core_score"), "worst_family_score": report.get("worst_family_score"), "passed": report.get("passed"), "valid": report.get("valid"), "reason": report.get("reason", report.get("evaluator_execution_error"))}), flush=True)
        output = {"completed": completed, "pending": [concept for concept in jobs if concept not in completed]}
        temporary = arguments.output.with_suffix(".tmp.json")
        temporary.write_text(json.dumps(output, indent=2) + "\n")
        temporary.replace(arguments.output)
        if not arguments.watch or len(completed) == len(jobs):
            return
        time.sleep(15)


if __name__ == "__main__":
    main()
