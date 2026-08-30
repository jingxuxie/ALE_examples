import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from objective import validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request")
    parser.add_argument("response")
    arguments = parser.parse_args()
    request = json.loads(Path(arguments.request).read_text())
    response = json.loads(Path(arguments.response).read_text())
    solutions = {entry["id"]: entry for entry in response["solutions"]}
    ratios = []
    families = defaultdict(list)
    for case in request["cases"]:
        value = validate(case, solutions[case["id"]])
        baseline = case["baseline_cost"]
        ratio = value / baseline
        ratios.append(ratio)
        families[case["family"]].append(ratio)
    reduction = lambda values: 1 - math.exp(sum(math.log(value) for value in values) / len(values))
    report = {"core_score": reduction(ratios), "family_scores": {key: reduction(values) for key, values in families.items()}}
    report["worst_family_score"] = min(report["family_scores"].values())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
