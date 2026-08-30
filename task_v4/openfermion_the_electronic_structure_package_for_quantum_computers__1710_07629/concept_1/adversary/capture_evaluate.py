import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
import evaluate as trusted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    arguments = parser.parse_args()
    original = trusted.score

    def record(request, response, elapsed, artifact=False):
        result = original(request, response, elapsed, artifact)
        arguments.response.write_text(json.dumps(response, allow_nan=False))
        return result

    trusted.score = record
    try:
        result = trusted.evaluate(arguments.submission, arguments.cases)
    except Exception as error:
        result = {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": str(error)}
    arguments.report.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
