from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def evaluate_when_finished(pair):
    concept_number, attempt_number = pair
    concept = ROOT / f"concept_{concept_number}"
    evidence = concept / "attempts" / f"v_{attempt_number}_evidence"
    output = concept / "attempts" / f"v_{attempt_number}"
    while True:
        try:
            metadata = json.loads((evidence / "launch.json").read_text())
        except (OSError, ValueError):
            metadata = {}
        if "participant_unchanged" in metadata:
            break
        time.sleep(10)
    report_path = evidence / "score.json"
    if report_path.exists():
        return json.loads(report_path.read_text())
    if not metadata["participant_unchanged"]:
        report = {"passed": False, "valid": False, "core_score": 0.0, "reason": "participant assets changed during fresh attempt"}
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        return report
    command = ["/usr/bin/python3", "-B", str(concept / "evaluator/evaluate.py")]
    if concept_number == 1:
        command += ["--policy", str(output / "policy.json"), "--split", "hidden", "--jobs", "8", "--output", str(report_path)]
    elif concept_number == 2:
        command += ["--submission", str(output), "--report", str(report_path)]
    else:
        command += ["--policy", str(output / "policy.py"), "--jobs", "12", "--output", str(report_path)]
    started = time.monotonic()
    with (evidence / "evaluation.log").open("w") as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    execution = {"command": command, "returncode": process.returncode, "elapsed_seconds": time.monotonic() - started}
    (evidence / "evaluation_execution.json").write_text(json.dumps(execution, indent=2) + "\n")
    if process.returncode != 0 or not report_path.exists():
        report = {"passed": False, "valid": False, "reason": "evaluation process failed; inspect log before hardness decision"}
    else:
        report = json.loads(report_path.read_text())
    summary = {"concept": concept_number, "attempt": attempt_number, **{key: report.get(key) for key in ("core_score", "worst_family_score", "passed", "valid", "reason")}}
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", type=int, choices=(1, 2, 3))
    parser.add_argument("--attempt", type=int)
    arguments = parser.parse_args()
    if (arguments.concept is None) != (arguments.attempt is None):
        parser.error("concept and attempt must be supplied together")
    pairs = [(arguments.concept, arguments.attempt)] if arguments.concept is not None else [(1, 1), (2, 2), (2, 3), (3, 1)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(evaluate_when_finished, pairs))
