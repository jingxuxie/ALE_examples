import itertools
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from measure import HERE


def main():
    variants = []
    for path in sorted((HERE / "results").glob("*.json")):
        report = json.loads(path.read_text())
        if report.get("valid") and "spec" in report and not report["spec"].get("json_protocol"):
            variants.append(report)
    best = None
    base = variants[0]["cases"]
    for length in range(1, min(4, len(variants)) + 1):
        for selected in itertools.combinations(variants, length):
            cpu = sum(item["cpu_seconds"] for item in selected)
            if cpu > 68 or sum(item["elapsed_seconds"] for item in selected) > 105:
                continue
            costs = [min(item["cases"][index]["cost"] for item in selected) for index in range(len(base))]
            value = sum(math.log(cost / row["baseline_cost"]) for cost, row in zip(costs, base)) / len(base)
            if best is None or (value, cpu) < (best[0], best[1]):
                best = (value, cpu, selected, costs)
    result = {"configs": [item["spec"] for item in best[2]], "predicted_core_score": 1 - math.exp(best[0]), "measured_cpu_sum": best[1], "measured_wall_sum": sum(item["elapsed_seconds"] for item in best[2]), "cost": sum(best[3]), "classification": "Selection for an actual generic portfolio, not a passing runtime proof."}
    (HERE / "portfolio_selection.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
