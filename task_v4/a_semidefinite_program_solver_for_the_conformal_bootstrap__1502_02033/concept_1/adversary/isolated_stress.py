import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from oracle import LebesgueOracle
from runner import run_solution


def main():
    results = []
    for identifier in ["six_scenario_boundary_04", "six_scenario_boundary_12"]:
        case = json.loads((ROOT / "adversary/champion_search/cases" / (identifier + ".json")).read_text())
        case = case.get("input", case)
        row = {"id": identifier}
        for label, source in [("baseline", ROOT / "participant/baseline/solution.py"),
                              ("champion", ROOT / "champions/generation_1/solution.py")]:
            output, timing = run_solution(source, json.dumps(case))
            row[label] = {"timing": timing, "enclosure": LebesgueOracle(case, output).supremum()}
            print(identifier, label, timing["cpu_seconds"], flush=True)
        row["quality_ratio"] = math.exp(row["baseline"]["enclosure"]["log_lower"] - row["champion"]["enclosure"]["log_upper"])
        row["no_regression"] = row["quality_ratio"] >= 1.0
        results.append(row)
    report = {"passed": all(row["no_regression"] for row in results), "cases": results,
              "isolation": "bubblewrap-required", "resource_accounting": "protected direct-parent wait4",
              "scope": "two timer-limited stress cases selected by the 160-case private search"}
    (ROOT / "adversary/isolated_stress.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "quality_ratios": [row["quality_ratio"] for row in results]}, indent=2))


if __name__ == "__main__":
    main()
