import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/baseline"))
from fleet import load_fleet, route_array


def ring_bounds(data):
    case = data["configuration"]
    sensors = {sensor["sensor_id"]: sensor for sensor in case["sensors"]}
    actions = case["actions"]
    probe = case["calibration_test"]
    valid_open = [index for index, action in enumerate(actions) if action["cost"] <= case["total_budget"]]
    bounds = []
    for prior in data["priors"]:
        open_loss = float(np.min((prior @ data["table"]["open"])[valid_open]))
        probe_loss = 0.0
        for result_index, result in enumerate(probe["results"]):
            weights = prior * data["likelihood"][result_index]
            first_losses = []
            for first_id in probe["allowed_first_sensor_ids"][result]:
                first_loss = 0.0
                for sector, second_ids in enumerate(probe["allowed_second_sensor_ids_by_sector"][first_id]):
                    second_losses = []
                    for second_id in second_ids:
                        spent = probe["cost"] + sensors[first_id]["cost"] + sensors[second_id]["cost"]
                        allowed = [index for index, action in enumerate(actions) if spent + action["cost"] <= case["total_budget"]]
                        if allowed:
                            weighted = np.einsum("q,qoa->oa", weights, route_array(data, first_id, sector, second_id))
                            second_losses.append(float(np.sum(np.min(weighted[:, allowed], axis=1))))
                    first_loss += min(second_losses, default=float("inf"))
                first_losses.append(first_loss)
            probe_loss += min(first_losses, default=float("inf"))
        bounds.append(min(open_loss, probe_loss))
    return bounds


def main():
    suite = json.loads((ROOT / "evaluator/hidden/suite.json").read_text())["fleets"]
    baseline = json.loads((ROOT / "evaluator/hidden/baseline.json").read_text())["fleets"]
    records = []
    family_bounds = {}
    for entry in suite:
        manifest, cases = load_fleet(ROOT / "evaluator/hidden" / entry["directory"])
        bounds = [ring_bounds(data) for data in cases]
        lower = max(max(values) for values in bounds)
        guarded_lower = max(0.0, lower - 1e-4)
        upper_gain = 100 * (1 - guarded_lower / baseline[entry["id"]]["objective"])
        family_bounds.setdefault(entry["family"], []).append(upper_gain)
        records.append({"fleet": entry["id"], "family": entry["family"], "relaxed_objective_lower_bound": lower, "guarded_lower_bound": guarded_lower, "improvement_upper_bound_percent": upper_gain, "ring_scenario_bounds": bounds})
    families = {name: float(np.mean(values)) for name, values in family_bounds.items()}
    report = {"relaxation": "Each ring and each prior scenario may choose its own Bayes-optimal adaptive tree, without any fleet capacity or shared-design restriction. Realized path budgets and admissible measurement routes remain enforced.", "numeric_guard_in_loss": 1e-4, "core_improvement_upper_bound_percent": float(np.mean(list(families.values()))), "worst_family_improvement_upper_bound_percent": min(families.values()), "family_improvement_upper_bounds_percent": families, "fleets": records, "note": "This is a lower bound from the validated response catalogs, not a feasible fleet planner. It can rule out excessive improvement targets but cannot establish achievability."}
    (ROOT / "adversary/relaxed_bound.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "fleets"}, indent=2))


if __name__ == "__main__":
    main()
