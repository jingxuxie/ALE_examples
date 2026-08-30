import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--attempt-index", type=int)
    parser.add_argument("concepts", nargs="+", choices=["concept_1", "concept_2", "concept_3"])
    arguments = parser.parse_args()
    pending = set(arguments.concepts)
    while pending:
        for name in sorted(pending):
            concept = ROOT / name
            attempt_index = arguments.attempt_index or arguments.generation
            attempt = concept / "attempts" / f"v_{attempt_index}"
            record_path = attempt.parent / (attempt.name + "_runner.json")
            try:
                record = json.loads(record_path.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            if "finished_utc" not in record:
                continue
            artifact = attempt / "design.json" if name == "concept_2" else attempt
            result_path = attempt.parent / (attempt.name + "_score.json")
            command = [sys.executable, str(concept / "evaluator" / "evaluate.py"), str(artifact),
                       "--output", str(result_path)]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=1000)
            (attempt.parent / (attempt.name + "_evaluation.log")).write_text(result.stdout)
            if result_path.exists():
                score = json.loads(result_path.read_text())
            else:
                score = {"valid": False, "passed": False, "reason": "evaluator did not produce result",
                         "returncode": result.returncode, "log": result.stdout[-2000:]}
                result_path.write_text(json.dumps(score, indent=2) + "\n")
            print(json.dumps({"concept": name, "generation": arguments.generation, "attempt_index": attempt_index,
                              "core_score": score.get("core_score"),
                              "worst_family_score": score.get("worst_family_score"),
                              "valid": score.get("valid"), "passed": score.get("passed"),
                              "reason": score.get("reason")}), flush=True)
            pending.remove(name)
        if pending:
            time.sleep(20)


if __name__ == "__main__":
    main()
