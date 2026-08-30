import argparse
import importlib.util
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    for name in ("evaluator", "submission", "cases", "report", "response"):
        parser.add_argument("--" + name, type=Path, required=True)
    arguments = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(arguments.evaluator.resolve().parent))
    specification = importlib.util.spec_from_file_location("trusted_gauge_evaluator", arguments.evaluator)
    trusted = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(trusted)
    original = trusted.score

    def record(request, response, elapsed, artifact=False):
        result = original(request, response, elapsed, artifact)
        arguments.response.write_text(json.dumps(response, allow_nan=False))
        return result

    trusted.score = record
    try:
        report = trusted.evaluate(arguments.submission, arguments.cases)
    except Exception as error:
        report = {"core_score": 0.0, "worst_family_score": 0.0, "valid": False, "passed": False, "reason": str(error)}
    report["diagnostic_only"] = True
    report["reference_note"] = "Unrotated input costs are diagnostic denominators, not champion-ratchet benchmark references."
    arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: report.get(key) for key in ("valid", "passed", "reason", "runtime_seconds", "diagnostic_only")}), flush=True)


if __name__ == "__main__":
    main()
