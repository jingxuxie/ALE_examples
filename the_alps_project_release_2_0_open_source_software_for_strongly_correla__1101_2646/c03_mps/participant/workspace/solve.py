import argparse
import json
from pathlib import Path

from baseline import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case = json.loads(Path(args.input).read_text())
    result = solve(case)
    Path(args.output).write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
