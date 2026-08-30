"""Execute the canonical baseline with explicit writable output locations."""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="predictions.npz in a writable output directory")
    parser.add_argument("--report", type=Path,
                        help="writable report path; defaults beside predictions")
    parser.add_argument("--data", type=Path,
                        help="optional data directory; defaults to canonical supplied data")
    args = parser.parse_args()
    report = args.report if args.report is not None else args.output.with_name("baseline_report.json")
    canonical = Path(__file__).resolve().parents[1] / "input/workspace/baseline/predict.py"
    command = [sys.executable, "-B", str(canonical), "--output", str(args.output),
               "--report", str(report)]
    if args.data is not None:
        command.extend(["--data", str(args.data)])
    os.execv(sys.executable, command)


if __name__ == "__main__":
    main()
