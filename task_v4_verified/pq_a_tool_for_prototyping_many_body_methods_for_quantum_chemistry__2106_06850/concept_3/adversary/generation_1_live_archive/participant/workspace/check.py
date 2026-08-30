"""Local checker. Only the organizer's frozen evaluator determines final scores."""

import argparse
import json

from fermion import evaluate_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True)
    arguments = parser.parse_args()
    report = evaluate_path(arguments.submission)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
