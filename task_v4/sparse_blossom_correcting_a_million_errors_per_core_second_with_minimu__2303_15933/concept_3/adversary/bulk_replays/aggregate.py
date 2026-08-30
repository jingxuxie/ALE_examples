import json
import math
from pathlib import Path


def main():
    directory = Path(__file__).resolve().parent
    concept = directory.parents[1]
    official = json.loads((concept / "attempts/v_1_result.json").read_text())
    reports = [official]
    for index in range(1, 4):
        replay = json.loads((directory / f"tape_{index}_report.json").read_text())
        reports.append(replay["policies"]["candidate"])
    cells = {
        family: math.sqrt(sum(report["family_log_rmse"][family] ** 2 for report in reports) / len(reports))
        for family in official["family_log_rmse"]
    }
    result = {
        "supplementary_only": True,
        "replaces_official_score": False,
        "parameter_population": "Same 12 hidden parameter episodes; four independent observation-noise tapes, including the original tape",
        "policy": "Pristine first fresh submission, unchanged between all tapes",
        "aggregation": "Equal-noise-tape mean squared log errors within each regime/family, then square root",
        "family_log_rmse": cells,
        "mean_family_log_rmse": sum(cells.values()) / len(cells),
        "worst_regime_family_log_rmse": max(cells.values()),
        "official_passed": official["passed"],
        "caveat": "This is a post-hoc stability diagnostic, not a replacement benchmark or a generalization guarantee.",
    }
    (directory / "aggregate_analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
