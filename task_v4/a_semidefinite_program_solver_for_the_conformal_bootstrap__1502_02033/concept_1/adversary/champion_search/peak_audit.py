import json
import math
from pathlib import Path
import warnings

import numpy as np

from sweep import HERE, ROOT, LebesgueOracle, load_module, save


def main():
    champion = load_module("audit_champion", ROOT / "attempts" / "v_1" / "solution.py")
    records = []
    for name in ("screening.jsonl", "focused_screening.jsonl"):
        path = HERE / name
        if path.exists():
            records.extend(json.loads(line) for line in path.read_text().splitlines())
    rows = []
    for record in records:
        if not record["champion"]["valid_output"] or "champion" not in record.get("sampled_log_lower", {}):
            continue
        case = record["input"]
        scale = min(scenario["a"] for scenario in case["scenarios"])
        scenarios = [{"a": scenario["a"] / scale, "poles": [pole * scale for pole in scenario["poles"]]}
                     for scenario in case["scenarios"]]
        nodes = np.asarray(record["champion"]["output"]["nodes"]) * scale
        try:
            objective = champion.PeakObjective(case["degree"], scenarios, free_origin=nodes[0] > 0)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                claimed = float(objective.peaks(nodes, iterations=18).max())
            sampled = record["sampled_log_lower"]["champion"]
            row = {"id": record["id"], "family": record["family"], "champion_internal_log_peak": claimed,
                   "independent_sampled_log_lower": sampled, "log_underestimate": sampled - claimed}
            if sampled > claimed + math.log(1.005):
                row["enclosure"] = LebesgueOracle(case, record["champion"]["output"]).supremum()
            rows.append(row)
        except Exception as error:
            rows.append({"id": record["id"], "error": type(error).__name__ + ": " + str(error)})
    rows.sort(key=lambda row: row.get("log_underestimate", -math.inf), reverse=True)
    save(HERE / "peak_audit.json", {"examined": len(rows), "rows": rows,
                                    "significant_underestimates": sum(row.get("log_underestimate", 0) > math.log(1.005) for row in rows)})
    print(json.dumps(rows[:8], indent=2))


if __name__ == "__main__":
    main()
