import argparse
import importlib.util
import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    started = time.monotonic()
    try:
        source = ROOT / "evaluator/hidden/checker.py"
        specification = importlib.util.spec_from_file_location("locked_checker", source)
        checker = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(checker)
        submission = Path(arguments.submission)
        if submission.is_dir():
            submission = submission / "answer.json"
        if submission.is_symlink() or submission.stat().st_size > 4_000_000:
            raise ValueError("submission must be a regular small JSON file")
        answer = json.loads(submission.read_text())
        instances = json.loads((ROOT / "evaluator/hidden/instances.json").read_text())["instances"]
        result = checker.score(instances, answer)
    except Exception as error:
        result = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
                  "valid": False, "passed": False, "reason": f"invalid submission: {error}"}
    result["evaluation_seconds"] = time.monotonic() - started
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
