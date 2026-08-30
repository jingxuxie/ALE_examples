import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from pair_model import increments


def main():
    hidden = ROOT / "evaluator/hidden"
    report = json.loads((hidden / "baseline_score.json").read_text())
    tables = np.load(hidden / "cases.npz")["energies"]
    diagnostics = json.loads((hidden / "diagnostics.json").read_text())
    failures = []
    for record, table, diagnostic in zip(report["records"], tables, diagnostics):
        if abs(record["error"]) <= 2.5e-5:
            continue
        terms = increments(table)
        order_sums = [sum(value for mask, value in enumerate(terms) if mask.bit_count() == order) for order in range(1, 9)]
        higher_tail = sum(order_sums[4:])
        selected_four_error = record["error"] + higher_tail
        if abs(higher_tail) > abs(selected_four_error):
            category = "higher_than_four_body_resurgence"
        else:
            category = "parent_magnitude_selection_misses_four_body_aggregate"
        failures.append({"index": record["index"], "family": record["family"],
                         "error_hartree": record["error"], "category": category,
                         "order_sums_hartree": order_sums,
                         "five_and_higher_tail": higher_tail,
                         "unqueried_four_body_error": selected_four_error,
                         "reference_weight": diagnostic["reference_weight"],
                         "gap": diagnostic["gap"], "eigenpair_residual": diagnostic["residual"]})
    output = {"tested_cases": len(tables), "admissible_cases": len(tables),
              "absolute_error_over_25_microhartree": len(failures),
              "failure_clusters": dict(Counter(item["category"] for item in failures)),
              "failures": failures,
              "scope": "Privileged diagnostic of initial baseline; not a passing policy or a fresh-agent attempt."}
    (ROOT / "adversary/baseline_failure_clusters.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "failures"}, indent=2))


if __name__ == "__main__":
    main()
