import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def argument_names(evaluator):
    names = set()
    for node in ast.walk(ast.parse(evaluator.read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    names.add(argument.value)
    return names


def score_result(result_path):
    run = result_path.parent
    if (run / "evaluation_complete.json").exists():
        return None
    if (run / "adjudication.json").exists():
        adjudication = json.loads((run / "adjudication.json").read_text())
        if not adjudication.get("competitive", True):
            return None
    metadata = json.loads(result_path.read_text())
    concept_name = metadata["concept"]
    evaluator = ROOT / concept_name / "evaluator" / "evaluate.py"
    submission = Path(metadata["frozen_submission"])
    report = run / "evaluation.json"
    required = submission / ("witness.npz" if concept_name == "concept_2" else "solve.py")
    if not metadata["participant_unchanged"]:
        outcome = {"passed": False, "valid": False, "administratively_invalid": True,
                   "reason": "Participant assets changed during the run; isolation/integrity requires investigation."}
        report.write_text(json.dumps(outcome, indent=2) + "\n")
        returncode = None
    elif not required.is_file() or required.is_symlink():
        outcome = {"core_score": 0.0, "worst_family_score": 0.0, "passed": False, "valid": False,
                   "reason": "No regular top-level " + required.name + " in the deadline-frozen submission.",
                   "submission_missing": True, "timed_out": metadata["timed_out"]}
        report.write_text(json.dumps(outcome, indent=2) + "\n")
        returncode = None
    else:
        flags = argument_names(evaluator)
        command = [sys.executable, str(evaluator)]
        if concept_name == "concept_2":
            command += ["--artifact", str(required), "--output", str(report),
                        "--audit-output", str(run / "evaluation_audit.json")]
        else:
            command += ["--candidate" if "--candidate" in flags else "--submission", str(submission)]
            command += ["--report" if "--report" in flags else "--output", str(report)]
        environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
        with (run / "evaluation.log").open("w") as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment,
                                       stdin=subprocess.DEVNULL)
        returncode = completed.returncode
        if report.exists():
            outcome = json.loads(report.read_text())
        else:
            outcome = {"passed": False, "valid": False, "administratively_invalid": True,
                       "reason": "Evaluator failed without a machine-readable report; inspect evaluation.log."}
            report.write_text(json.dumps(outcome, indent=2) + "\n")
    completion = {"concept": concept_name, "attempt": metadata["attempt"], "returncode": returncode,
                  "passed": bool(outcome.get("passed", outcome.get("valid", outcome.get("success", False)))),
                  "administratively_invalid": outcome.get("administratively_invalid", False),
                  "report": str(report), "finished_unix": time.time()}
    (run / "evaluation_complete.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion), flush=True)
    return completion


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch-seconds", type=int, default=0)
    arguments = parser.parse_args()
    deadline = time.monotonic() + arguments.watch_seconds
    while True:
        if (ROOT / "authoring" / "STOP_SCORING").exists():
            return
        for result_path in sorted((ROOT / "authoring" / "runs").glob("concept_*/v_*/result.json")):
            score_result(result_path)
        if time.monotonic() >= deadline:
            return
        time.sleep(5)


if __name__ == "__main__":
    main()
