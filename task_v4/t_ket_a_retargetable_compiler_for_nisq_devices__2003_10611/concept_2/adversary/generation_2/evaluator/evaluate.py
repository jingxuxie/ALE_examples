import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))

from benchmark import evaluate_file


def evaluate(solution_dir, output_dir=None):
    result = evaluate_file(Path(solution_dir).resolve() / "witness.json")
    if output_dir is not None:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("solution_dir", nargs="?", type=Path)
    parser.add_argument("--solution-dir", dest="solution_option", type=Path)
    parser.add_argument("--output-dir", type=Path)
    arguments = parser.parse_args()
    solution = arguments.solution_option or arguments.solution_dir
    if solution is None:
        parser.error("a solution directory containing witness.json is required")
    print(json.dumps(evaluate(solution, arguments.output_dir), sort_keys=True))


if __name__ == "__main__":
    main()
