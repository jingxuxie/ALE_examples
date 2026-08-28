import json
import math
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
PILOT = ROOT / "pilots" / "c02_multiscale_protection"


def audit(split="screening"):
    rows = []
    floors = {"density": 0.001, "violation": 0.00002, "correlation": 0.0001}
    for path in sorted((PILOT / "private" / "challenge_pool" / split).glob("*.json")):
        record = json.loads(path.read_text())
        lower_bounds = {}
        ranges = {}
        for name, floor in floors.items():
            values = np.array(record["reference"][name])
            scale = max(float(np.sqrt(np.mean(values**2))), floor)
            bound = record["audit"]["max_differences"][name]
            lower_bounds[name] = math.exp(-math.log(10) * bound / scale)
            ranges[name] = [float(values.min()), float(values.max())]
        minimum_score = float(np.prod(list(lower_bounds.values())) ** 0.25)
        rows.append({"id": record["id"], "family": record["family"],
                     "coarse_vs_fine_score_lower_bound": minimum_score,
                     "block_lower_bounds": lower_bounds, "ranges": ranges,
                     "parameter_recovery_error": record["audit"]["calibration_parameter_error"],
                     "fine_seconds": record["audit"]["fine"]["seconds"],
                     "needs_refinement": minimum_score < 0.97})
    result = {"split": split, "case_count": len(rows), "cases": rows,
              "all_available_cases_converged": bool(rows) and not any(row["needs_refinement"] for row in rows),
              "interpretation": "Convergence diagnostic, not a rigorous bound on the exact many-body solution."}
    destination = PILOT / "private" / "reference" / (split + "_convergence_audit.json")
    destination.write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    import sys
    audit(sys.argv[1] if len(sys.argv) > 1 else "screening")
