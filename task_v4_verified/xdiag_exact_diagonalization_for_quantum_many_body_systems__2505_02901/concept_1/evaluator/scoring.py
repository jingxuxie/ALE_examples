import json

import numpy as np

from physics import QuantumCase


class InvalidPolicy(ValueError):
    pass


def strict_json(text):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InvalidPolicy("duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise InvalidPolicy("nonfinite JSON number")

    result = json.loads(text, object_pairs_hook=object_pairs, parse_constant=invalid_constant)

    def finite(value):
        if isinstance(value, float) and not np.isfinite(value):
            raise InvalidPolicy("nonfinite JSON number")
        if isinstance(value, dict):
            for entry in value.values():
                finite(entry)
        if isinstance(value, list):
            for entry in value:
                finite(entry)

    finite(result)
    return result


def keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise InvalidPolicy("incorrect fields in " + label)


def identifier_list(value, allowed, maximum, label):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InvalidPolicy("invalid " + label)
    if len(value) > maximum or len(value) != len(set(value)) or not set(value) <= set(allowed):
        raise InvalidPolicy("invalid selection in " + label)


def validate(manifest, configurations, output):
    keys(output, ("fleet_id", "shared_sensors", "shared_actions", "cases"), "fleet")
    if output["fleet_id"] != manifest["fleet_id"]:
        raise InvalidPolicy("incorrect fleet_id")
    identifier_list(output["shared_sensors"], manifest["sensor_usage_caps"],
                    manifest["shared_sensor_count"], "shared_sensors")
    identifier_list(output["shared_actions"], manifest["action_usage_caps"],
                    manifest["shared_action_count"], "shared_actions")
    if not isinstance(output["cases"], list) or len(output["cases"]) != len(configurations):
        raise InvalidPolicy("missing or extra case")
    sensor_usage = dict.fromkeys(manifest["sensor_usage_caps"], 0)
    action_usage = dict.fromkeys(manifest["action_usage_caps"], 0)
    for case, policy in zip(configurations, output["cases"]):
        if not isinstance(policy, dict) or policy.get("case_id") != case["case_id"]:
            raise InvalidPolicy("case order or identifier mismatch")
        action_map = {action["action_id"]: action for action in case["actions"]}
        sensor_map = {sensor["sensor_id"]: sensor for sensor in case["sensors"]}

        def use_action(identifier, spent):
            if not isinstance(identifier, str) or identifier not in output["shared_actions"]:
                raise InvalidPolicy("unmanufactured action")
            if identifier not in action_map or spent + action_map[identifier]["cost"] > case["total_budget"]:
                raise InvalidPolicy("path budget exceeded")
            action_usage[identifier] += 1

        def use_sensor(identifier):
            if not isinstance(identifier, str) or identifier not in output["shared_sensors"]:
                raise InvalidPolicy("unmanufactured sensor")
            if identifier not in sensor_map:
                raise InvalidPolicy("unknown sensor")
            sensor_usage[identifier] += 1

        if policy.get("root") == "open":
            keys(policy, ("case_id", "root", "action"), "open policy")
            use_action(policy["action"], 0)
        elif policy.get("root") == "probe":
            keys(policy, ("case_id", "root", "branches"), "probe policy")
            probe = case["calibration_test"]
            if not isinstance(policy["branches"], list) or len(policy["branches"]) != len(probe["results"]):
                raise InvalidPolicy("calibration branch count")
            for result, branch in zip(probe["results"], policy["branches"]):
                keys(branch, ("first_sensor", "seconds"), "first branch")
                first_id = branch["first_sensor"]
                use_sensor(first_id)
                if first_id not in probe["allowed_first_sensor_ids"][result]:
                    raise InvalidPolicy("disallowed first sensor")
                first = sensor_map[first_id]
                if not isinstance(branch["seconds"], list) or len(branch["seconds"]) != first["order"]:
                    raise InvalidPolicy("first-sector branch count")
                for sector, second in enumerate(branch["seconds"]):
                    keys(second, ("second_sensor", "actions"), "second branch")
                    second_id = second["second_sensor"]
                    use_sensor(second_id)
                    if second_id not in probe["allowed_second_sensor_ids_by_sector"][first_id][sector]:
                        raise InvalidPolicy("disallowed second sensor")
                    sensor = sensor_map[second_id]
                    if sensor["time"] <= first["time"]:
                        raise InvalidPolicy("noncausal sensor order")
                    if not isinstance(second["actions"], list) or len(second["actions"]) != sensor["order"]:
                        raise InvalidPolicy("second-sector leaf count")
                    for action in second["actions"]:
                        use_action(action, probe["cost"] + first["cost"] + sensor["cost"])
        else:
            raise InvalidPolicy("unknown root")
    for identifier, usage in sensor_usage.items():
        if usage > manifest["sensor_usage_caps"][identifier]:
            raise InvalidPolicy("sensor capacity exceeded: " + identifier)
    for identifier, usage in action_usage.items():
        if usage > manifest["action_usage_caps"][identifier]:
            raise InvalidPolicy("action capacity exceeded: " + identifier)
    return sensor_usage, action_usage


def exact_score(manifest, configurations, output):
    sensor_usage, action_usage = validate(manifest, configurations, output)
    scenario_losses = {}
    for case, policy in zip(configurations, output["cases"]):
        model = QuantumCase(case, propagators=False)
        action_indices = {action["action_id"]: index for index, action in enumerate(case["actions"])}
        if policy["root"] == "open":
            regime_losses = model.open_table()[:, action_indices[policy["action"]]]
        else:
            regime_losses = np.zeros(len(case["regimes"]))
            probe = case["calibration_test"]
            for result, branch in zip(probe["results"], policy["branches"]):
                likelihood = np.array([probe["likelihood_by_regime"][regime["regime_id"]][result]
                                       for regime in case["regimes"]])
                for sector, second in enumerate(branch["seconds"]):
                    probability, numerator = model.route(branch["first_sensor"], sector, second["second_sensor"])
                    for outcome, action in enumerate(second["actions"]):
                        regime_losses += likelihood * numerator[:, outcome, action_indices[action]]
        case_losses = {}
        for scenario in case["prior_scenarios"]:
            prior = np.array([scenario["prior"][regime["regime_id"]] for regime in case["regimes"]])
            loss = float(prior @ regime_losses)
            if not np.isfinite(loss) or loss < -1e-8 or loss > 1 + case["imbalance_weight"] + 1e-7:
                raise ValueError("invalid independently computed quantum loss")
            case_losses[scenario["scenario_id"]] = loss
        scenario_losses[case["case_id"]] = case_losses
    worst = max(loss for case in scenario_losses.values() for loss in case.values())
    return {"objective": worst, "scenario_losses": scenario_losses,
            "sensor_usage": sensor_usage, "action_usage": action_usage}
