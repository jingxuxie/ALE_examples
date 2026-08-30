import argparse
import json
import math
import os
from pathlib import Path
import stat

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ROW_BITS = np.array([[(mask >> row) & 1 for row in range(4)] for mask in range(16)])
VERTICAL_BITS = ROW_BITS[:8, :3]
VERTICAL_PARITIES = np.arange(8) ^ (np.arange(8) << 1)
PARITIES = ROW_BITS.sum(axis=1) % 2


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def load_submission(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16384:
            raise ValueError("submission must be a regular file of at most 16384 bytes")
        encoded = source.read(16385)
    if len(encoded) > 16384:
        raise ValueError("oversized submission")
    data = json.loads(encoded.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    validate(data)
    return data


def validate(data):
    if type(data) is not dict or set(data) != {"version", "probabilities", "syndrome"}:
        raise ValueError("exact keys: version, probabilities, syndrome")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("version must be integer 1")
    rates = data["probabilities"]
    if type(rates) is not list or len(rates) != 39:
        raise ValueError("39 edge probabilities required")
    if any(type(rate) not in (int, float) or not math.isfinite(rate) or not 0.02 <= rate <= 0.14 for rate in rates):
        raise ValueError("probabilities must be finite non-boolean numbers in [0.02, 0.14]")
    mean = math.fsum(rates) / 39
    deviation = math.sqrt(math.fsum((rate - mean) ** 2 for rate in rates) / 39)
    if mean > 0.085 or deviation < 0.015:
        raise ValueError("mean must be <= 0.085 and population standard deviation >= 0.015")
    syndrome = data["syndrome"]
    if type(syndrome) is not list or not 3 <= len(syndrome) <= 6:
        raise ValueError("syndrome must contain 3 through 6 detector indices")
    if any(type(detector) is not int or not 0 <= detector < 20 for detector in syndrome):
        raise ValueError("detectors must be integers in [0, 19], not booleans")
    if syndrome != sorted(set(syndrome)):
        raise ValueError("syndrome must be sorted and distinct")
    if len({detector // 4 for detector in syndrome}) < 3 or len({detector % 4 for detector in syndrome}) < 3:
        raise ValueError("syndrome must occupy at least three columns and three rows")


def frontier(probabilities, syndrome, scale=1.0):
    rates = np.asarray(probabilities, dtype=np.float64) * scale
    weights = np.log1p(-rates) - np.log(rates)
    horizontal = rates[:24].reshape(6, 4)
    horizontal_weights = weights[:24].reshape(6, 4)
    vertical = rates[24:].reshape(5, 3)
    vertical_weights = weights[24:].reshape(5, 3)
    horizontal_mass = np.prod(np.where(ROW_BITS[None, :, :], horizontal[:, None, :], 1 - horizontal[:, None, :]), axis=2)
    horizontal_cost = horizontal_weights @ ROW_BITS.T
    vertical_mass = np.prod(np.where(VERTICAL_BITS[None, :, :], vertical[:, None, :], 1 - vertical[:, None, :]), axis=2)
    vertical_cost = vertical_weights @ VERTICAL_BITS.T
    masses = np.zeros((2, 16))
    costs = np.full((2, 16), np.inf)
    masses[PARITIES, np.arange(16)] = horizontal_mass[0]
    costs[PARITIES, np.arange(16)] = horizontal_cost[0]
    syndrome_mask = sum(1 << detector for detector in syndrome)
    for column in range(5):
        required = (syndrome_mask >> (4 * column)) & 15
        incoming = np.arange(16)[:, None] ^ VERTICAL_PARITIES[None, :] ^ required
        masses = np.sum(masses[:, incoming] * vertical_mass[column][None, None, :], axis=2) * horizontal_mass[column + 1]
        costs = np.min(costs[:, incoming] + vertical_cost[column][None, None, :], axis=2) + horizontal_cost[column + 1]
    return masses.sum(axis=1), costs.min(axis=1)


def summarize(data, values, spec):
    center = values[len(values) // 2]
    physical = int(center[1][1] < center[1][0])
    opposite = 1 - physical
    records = []
    for scale, (joint, costs) in zip(spec["anchors"], values):
        total = float(sum(joint))
        records.append({"scale": scale, "joint_probabilities": list(map(float, joint)),
                        "class_costs": list(map(float, costs)), "syndrome_probability": total,
                        "signed_gap": float(costs[opposite] - costs[physical]),
                        "opposite_posterior": float(joint[opposite] / total),
                        "opposite_log_odds": math.log(float(joint[opposite] / joint[physical]))})
    lower, upper = spec["scale_interval"]
    derivative_bound = 39 / lower + math.fsum(rate / (1 - upper * rate) for rate in data["probabilities"])
    radius = max(right - left for left, right in zip(spec["anchors"], spec["anchors"][1:])) / 2
    allowance = derivative_bound * radius + spec["numerical_guard"]
    gap = min(record["signed_gap"] for record in records) - allowance
    log_odds = min(record["opposite_log_odds"] for record in records) - allowance
    posterior = 1 / (1 + math.exp(-log_odds))
    mass = min(record["syndrome_probability"] for record in records) * math.exp(-allowance)
    target = spec["targets"]
    normalized = [gap / target["gap"], log_odds / math.log(target["opposite_posterior"] / (1 - target["opposite_posterior"])), mass / target["syndrome_probability"]]
    failures = [name for name, ratio in zip(("gap", "opposite_posterior", "syndrome_probability"), normalized) if ratio < 1]
    worst_scale = min(min(record["signed_gap"] / target["gap"], record["opposite_log_odds"] / math.log(target["opposite_posterior"] / (1 - target["opposite_posterior"])), record["syndrome_probability"] / target["syndrome_probability"]) for record in records)
    return {"valid": True, "passed": gap >= target["gap"] and posterior >= target["opposite_posterior"] and mass >= target["syndrome_probability"],
            "reason": "certified_continuous_entropy_inversion" if not failures else "certified_targets_not_met: " + ", ".join(failures),
            "worst_scale_score": max(0.0, worst_scale), "worst_family_score": max(0.0, min(normalized)),
            "runtime_score": 1.0, "resource_score": 1.0,
            "core_score": max(0.0, min(normalized)), "physical_class": physical,
            "opposite_class": opposite, "certified_gap": gap, "certified_opposite_posterior": posterior,
            "certified_opposite_log_odds": log_odds, "certified_syndrome_probability": mass,
            "derivative_bound": derivative_bound, "cover_radius": radius, "allowance": allowance,
            "anchors": records}


def check(data):
    validate(data)
    spec = json.loads((ROOT / "input/spec.json").read_text())
    values = [frontier(data["probabilities"], data["syndrome"], scale) for scale in spec["anchors"]]
    return summarize(data, values, spec)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    try:
        result = check(load_submission(arguments.submission))
    except (ValueError, UnicodeError, OSError, OverflowError, RecursionError) as error:
        result = {"valid": False, "passed": False, "core_score": 0.0, "worst_scale_score": 0.0,
                  "worst_family_score": 0.0, "runtime_score": 0.0, "resource_score": 0.0,
                  "reason": "invalid_submission: " + str(error)}
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
