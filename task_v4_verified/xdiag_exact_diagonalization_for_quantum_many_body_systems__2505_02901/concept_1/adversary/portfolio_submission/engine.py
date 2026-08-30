import argparse
import itertools
import json
import time
import os
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np

from fleet import load_fleet, objective, policy_statistics, route_array


def probe_policy(data, sensor_set, action_set, sensor_remaining, action_remaining, weights):
    case = data["configuration"]
    probe = case["calibration_test"]
    sensors = {sensor["sensor_id"]: sensor for sensor in case["sensors"]}
    action_map = {action["action_id"]: action for action in case["actions"]}
    sensor_remaining, action_remaining = sensor_remaining.copy(), action_remaining.copy()
    branches = []
    for result_index, result in enumerate(probe["results"]):
        best = None
        posterior_weight = weights * data["likelihood"][result_index]
        for first in probe["allowed_first_sensor_ids"][result]:
            if first not in sensor_set or sensor_remaining[first] < 1:
                continue
            local_sensors, local_actions = sensor_remaining.copy(), action_remaining.copy()
            local_sensors[first] -= 1
            first_loss = np.zeros(len(case["regimes"]))
            seconds = []
            for sector, allowed in enumerate(probe["allowed_second_sensor_ids_by_sector"][first]):
                best_second = None
                for second in allowed:
                    if second not in sensor_set or local_sensors[second] < 1:
                        continue
                    available = [action for action in action_set
                                 if action_map[action]["cost"] + probe["cost"] + sensors[first]["cost"]
                                 + sensors[second]["cost"] <= case["total_budget"]]
                    remaining = local_actions.copy()
                    losses = np.zeros(len(case["regimes"]))
                    actions = []
                    route = route_array(data, first, sector, second)
                    for outcome in range(sensors[second]["order"]):
                        candidates = [action for action in available if remaining[action] > 0]
                        if not candidates:
                            break
                        chosen = min(candidates, key=lambda action: float(
                            posterior_weight @ route[:, outcome, data["action_index"][action]]))
                        actions.append(chosen)
                        remaining[chosen] -= 1
                        losses += route[:, outcome, data["action_index"][chosen]]
                    if len(actions) != sensors[second]["order"]:
                        continue
                    score = float(posterior_weight @ losses)
                    if best_second is None or score < best_second[0]:
                        best_second = score, second, actions, losses, remaining
                if best_second is None:
                    break
                score, second, actions, losses, local_actions = best_second
                first_loss += losses
                local_sensors[second] -= 1
                seconds.append({"second_sensor": second, "actions": actions})
            if len(seconds) != sensors[first]["order"]:
                continue
            score = float(posterior_weight @ first_loss)
            if best is None or score < best[0]:
                best = score, first, seconds, local_sensors, local_actions
        if best is None:
            return None
        score, first, seconds, sensor_remaining, action_remaining = best
        branches.append({"first_sensor": first, "seconds": seconds})
    return {"case_id": case["case_id"], "root": "probe", "branches": branches}


def solve(manifest, cases, trials=32, seed=710, diversify=False, deadline=None):
    random = np.random.RandomState(seed)
    sensor_ids = list(manifest["sensor_usage_caps"])
    action_ids = list(manifest["action_usage_caps"])
    first_ids = set(cases[0]["configuration"]["calibration_test"]["allowed_second_sensor_ids_by_sector"])
    sensor_sets = [selection for selection in itertools.combinations(sensor_ids, manifest["shared_sensor_count"])
                   if set(selection) & first_ids and set(selection) - first_ids]
    action_sets = list(itertools.combinations(action_ids, manifest["shared_action_count"]))
    best = None
    for trial in range(trials):
        if best is not None and deadline is not None and time.monotonic() >= deadline:
            break
        sensor_set = sensor_sets[random.randint(len(sensor_sets))]
        action_set = action_sets[random.randint(len(action_sets))]
        sensor_remaining = manifest["sensor_usage_caps"].copy()
        action_remaining = manifest["action_usage_caps"].copy()
        policies = []
        for data in cases:
            valid_actions = [action for action in data["configuration"]["actions"]
                             if action["action_id"] in action_set and action_remaining[action["action_id"]] > 0
                             and action["cost"] <= data["configuration"]["total_budget"]]
            if not valid_actions:
                break
            action = min(valid_actions, key=lambda entry: float(np.max(
                data["priors"] @ data["table"]["open"][:, data["action_index"][entry["action_id"]]])))["action_id"]
            action_remaining[action] -= 1
            policies.append({"case_id": data["configuration"]["case_id"], "root": "open", "action": action})
        if len(policies) != len(cases):
            continue
        order = sorted(range(len(cases)), key=lambda index: -float(np.max(policy_statistics(cases[index], policies[index])[0])))
        if diversify and trial % 3:
            random.shuffle(order)
        for index in order:
            data, old = cases[index], policies[index]
            action_remaining[old["action"]] += 1
            weights = np.mean(data["priors"], axis=0)
            if diversify and trial % 4:
                weights = random.dirichlet(np.full(len(data["priors"]), 0.35)) @ data["priors"]
            candidate = probe_policy(data, sensor_set, action_set, sensor_remaining, action_remaining, weights)
            if candidate is not None and np.max(policy_statistics(data, candidate)[0]) < np.max(policy_statistics(data, old)[0]):
                policies[index] = candidate
                losses, sensor_usage, action_usage = policy_statistics(data, candidate)
                for identifier, usage in sensor_usage.items():
                    sensor_remaining[identifier] -= usage
                for identifier, usage in action_usage.items():
                    action_remaining[identifier] -= usage
            else:
                action_remaining[old["action"]] -= 1
        value = objective(cases, policies)
        if best is None or value < best[0]:
            best = value, {"fleet_id": manifest["fleet_id"], "shared_sensors": list(sensor_set),
                           "shared_actions": list(action_set), "cases": policies}
    if best is None:
        raise RuntimeError("no feasible construction")
    return best[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    manifest, cases = load_fleet(arguments.input)
    result = solve(manifest, cases)
    Path(arguments.output).write_text(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
