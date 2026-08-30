import itertools
import math
import time

from core import generator_images, input_witness, weights_from_images


def compiled_schedule(layers):
    gates = []
    instances = []
    for round_index, layer in enumerate(layers):
        for qubit, word in enumerate(layer["local"]):
            for letter in word:
                if letter != "I":
                    gates.append((0 if letter == "H" else 1, qubit, 0, -1))
        for cx_index, (control, target) in enumerate(layer["cx"]):
            instances.append({"round": round_index, "cx_index": cx_index,
                              "control": control, "target": target})
            gates.append((2, control, target, len(instances) - 1))
    return gates, instances


def fault_rows(n, schedule, omitted):
    if len(omitted) > 3:
        raise ValueError("four or more omissions are unsupported")
    if len(set(omitted)) != len(omitted):
        raise ValueError("omission instances must be distinct")
    rows = [1 << position for position in range(2 * n)]
    first = omitted[0] if omitted else -1
    second = omitted[1] if len(omitted) > 1 else -1
    third = omitted[2] if len(omitted) > 2 else -1
    for kind, control, target, instance in schedule:
        if kind == 0:
            rows[control], rows[n + control] = rows[n + control], rows[control]
        elif kind == 1:
            rows[n + control] ^= rows[control]
        elif instance != first and instance != second and instance != third:
            rows[target] ^= rows[control]
            rows[n + control] ^= rows[n + target]
    return rows


def fault_weights(n, schedule, omitted):
    return tuple(weights_from_images(n, images)
                 for images in generator_images(n, fault_rows(n, schedule, omitted)))


def omission_profile(n, layers, maximum=3, minimum_weight=3, collect=False, on_scenario=None):
    if maximum not in (0, 1, 2, 3):
        raise ValueError("only zero through three distinct omissions are supported")
    if collect and maximum == 3:
        raise ValueError("three-omission sweeps must stream; use on_scenario instead of collect")
    started = time.perf_counter()
    schedule, instances = compiled_schedule(layers)
    by_count = {str(count): {"scenarios": 0, "failed_scenarios": 0, "minimum": n,
                            "minimum_histogram": [0] * (n + 1)} for count in range(maximum + 1)}
    names = ("forward.single", "forward.double", "inverse.single", "inverse.double")
    minima = {name: n for name in names}
    failure_counts = {name: 0 for name in names}
    global_minimum = n + 1
    witness = None
    records = [] if collect else None
    for count in range(maximum + 1):
        for omitted in itertools.combinations(range(len(instances)), count):
            weights = fault_weights(n, schedule, omitted)
            flattened = [values for strata in weights for values in strata]
            observed = [int(values.min()) for values in flattened]
            scenario_minimum = min(observed)
            entry = by_count[str(count)]
            entry["scenarios"] += 1
            entry["failed_scenarios"] += scenario_minimum < minimum_weight
            entry["minimum"] = min(entry["minimum"], scenario_minimum)
            entry["minimum_histogram"][scenario_minimum] += 1
            for name, value in zip(names, observed):
                minima[name] = min(minima[name], value)
                failure_counts[name] += value < minimum_weight
            if scenario_minimum < global_minimum:
                global_minimum = scenario_minimum
                index = observed.index(scenario_minimum)
                direction, stratum = names[index].split(".")
                witness = {"omissions": [instances[instance] for instance in omitted],
                           "direction": direction, "stratum": stratum,
                           "input": input_witness(n, stratum, int(flattened[index].argmin())),
                           "output_weight": scenario_minimum}
            if collect:
                records.append({"omitted_instances": list(omitted), "minima": observed})
            if on_scenario is not None:
                on_scenario(omitted, observed)
    expected = sum(math.comb(len(instances), count) for count in range(maximum + 1) if count <= len(instances))
    actual = sum(entry["scenarios"] for entry in by_count.values())
    if actual != expected:
        raise RuntimeError("fault enumeration count mismatch")
    for entry in by_count.values():
        if entry["scenarios"] == 0:
            entry["minimum"] = None
    result = {"max_omissions": maximum, "target_minimum": minimum_weight,
              "minimum": global_minimum, "core_score": min(1.0, global_minimum / minimum_weight),
              "passed": global_minimum >= minimum_weight, "scenarios": actual,
              "pauli_checks": actual * (6 * n + 9 * n * (n - 1)),
              "by_omission_count": by_count, "stratum_minima": minima,
              "failed_scenario_counts": failure_counts, "worst_witness": witness,
              "runtime_seconds": time.perf_counter() - started,
              "enumeration": "exhaustive; no sampling or early termination",
              "streaming": not collect, "max_live_scenarios": 1 if not collect else actual}
    if collect:
        result["instances"] = instances
        result["scenario_records"] = records
    return result
