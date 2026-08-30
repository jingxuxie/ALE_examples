import argparse
import json
from pathlib import Path

from design_common import aggregate, generate_supports, load_case, read_design, score_case


def main():
    parser = argparse.ArgumentParser(description="Exact public practice evaluator; no submissions are executed.")
    parser.add_argument("design", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--count", type=int, default=48)
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "input")
    arguments = parser.parse_args()
    if not 1 <= arguments.count <= 10000:
        parser.error("count must be between 1 and 10000 per family")
    axes = read_design(arguments.design)
    family = json.loads((arguments.input / "family.json").read_text())
    practice = json.loads((arguments.input / "practice.json").read_text())
    results = {}
    for case_index, identifier in enumerate(family["cases"]):
        case = load_case(arguments.input / (identifier + ".json.gz"))
        records = practice[identifier] if arguments.seed is None else generate_supports(case, arguments.seed + 37 * case_index, arguments.count, family["densities"])
        results[identifier] = score_case(case, records, axes)
    print(json.dumps(aggregate(results), indent=2))


if __name__ == "__main__":
    main()
