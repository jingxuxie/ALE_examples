import json
from pathlib import Path

import numpy as np


def load_fleet(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    cases = []
    for entry in manifest["cases"]:
        case = json.loads((directory / entry["configuration"]).read_text())
        with np.load(directory / entry["responses"], allow_pickle=False) as archive:
            table = {name: archive[name] for name in archive.files}
        regime_ids = [regime["regime_id"] for regime in case["regimes"]]
        priors = np.array([[scenario["prior"][identifier] for identifier in regime_ids]
                           for scenario in case["prior_scenarios"]])
        probe = case["calibration_test"]
        likelihood = np.array([[probe["likelihood_by_regime"][identifier][result]
                               for identifier in regime_ids] for result in probe["results"]])
        cases.append({"configuration": case, "table": table, "priors": priors,
                      "likelihood": likelihood,
                      "sensor_index": {sensor["sensor_id"]: index for index, sensor in enumerate(case["sensors"])},
                      "action_index": {action["action_id"]: index for index, action in enumerate(case["actions"])}})
    return manifest, cases


def route_array(data, first_id, sector, second_id):
    return data["table"]["route_{}_{}_{}".format(
        data["sensor_index"][first_id], sector, data["sensor_index"][second_id])]


def policy_statistics(data, policy):
    case = data["configuration"]
    sensors = {identifier: 0 for identifier in data["sensor_index"]}
    actions = {identifier: 0 for identifier in data["action_index"]}
    if policy["root"] == "open":
        actions[policy["action"]] += 1
        return data["priors"] @ data["table"]["open"][:, data["action_index"][policy["action"]]], sensors, actions
    regime_losses = np.zeros(len(case["regimes"]))
    for result, branch in enumerate(policy["branches"]):
        first = branch["first_sensor"]
        sensors[first] += 1
        for sector, second in enumerate(branch["seconds"]):
            sensors[second["second_sensor"]] += 1
            route = route_array(data, first, sector, second["second_sensor"])
            for outcome, action in enumerate(second["actions"]):
                actions[action] += 1
                regime_losses += data["likelihood"][result] * route[:, outcome, data["action_index"][action]]
    return data["priors"] @ regime_losses, sensors, actions


def objective(cases, policies):
    return max(float(np.max(policy_statistics(data, policy)[0]))
               for data, policy in zip(cases, policies))
