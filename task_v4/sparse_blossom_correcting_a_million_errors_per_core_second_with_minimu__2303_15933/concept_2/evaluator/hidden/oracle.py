import json
import math
import os
from pathlib import Path
import stat

import numpy as np


LOWER_SCALE = 0.95
UPPER_SCALE = 1.05
ANCHORS = tuple(0.95 + index * 0.005 for index in range(21))
GAP_TARGET = 1.08
POSTERIOR_TARGET = 0.85
MASS_TARGET = 0.0000175
GUARD = 1e-10


def read_artifact(path):
    def pairs_to_dict(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise ValueError("duplicate key")
            output[key] = value
        return output

    def invalid_constant(text):
        raise ValueError("nonfinite constant " + text)

    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16384:
            raise ValueError("artifact must be a regular file <= 16384 bytes")
        contents = stream.read(16385)
    if len(contents) > 16384:
        raise ValueError("artifact too large")
    artifact = json.loads(contents.decode("utf-8"), parse_constant=invalid_constant, object_pairs_hook=pairs_to_dict)
    if type(artifact) is not dict or set(artifact.keys()) != {"version", "syndrome", "probabilities"}:
        raise ValueError("incorrect artifact keys")
    if type(artifact["version"]) is not int or artifact["version"] != 1:
        raise ValueError("incorrect version")
    probabilities = artifact["probabilities"]
    if type(probabilities) is not list or len(probabilities) != 39:
        raise ValueError("incorrect probability vector shape")
    for probability in probabilities:
        if type(probability) not in (int, float):
            raise ValueError("probability must be a number, not a boolean")
        if not math.isfinite(probability) or probability < 0.02 or probability > 0.14:
            raise ValueError("probability outside finite bounds")
    average = math.fsum(probabilities) / 39
    spread = math.sqrt(math.fsum((probability - average) ** 2 for probability in probabilities) / 39)
    if average > 0.085 or spread < 0.015:
        raise ValueError("invalid mean or heterogeneity")
    detectors = artifact["syndrome"]
    if type(detectors) is not list or not 3 <= len(detectors) <= 6:
        raise ValueError("incorrect syndrome shape")
    if any(type(detector) is not int or detector < 0 or detector >= 20 for detector in detectors):
        raise ValueError("invalid detector index")
    if detectors != sorted(set(detectors)):
        raise ValueError("detector indices not sorted and unique")
    if len(set(detector // 4 for detector in detectors)) < 3 or len(set(detector % 4 for detector in detectors)) < 3:
        raise ValueError("syndrome not spatially spread")
    return artifact


def edge_masks():
    masks = []
    for cut in range(6):
        for row in range(4):
            if cut == 0:
                masks.append((1 << row) | (1 << 20))
            elif cut == 5:
                masks.append(1 << (16 + row))
            else:
                masks.append((1 << (4 * (cut - 1) + row)) | (1 << (4 * cut + row)))
    for column in range(5):
        for row in range(3):
            masks.append((1 << (4 * column + row)) | (1 << (4 * column + row + 1)))
    return masks


def full_state(probabilities, masks, detector_count, dtype=np.float64, return_all=False, target=0):
    count = 1 << (detector_count + 1)
    indices = np.arange(count, dtype=np.int64)
    masses = np.zeros(count, dtype=dtype)
    masses[0] = 1
    costs = np.full(count, np.inf, dtype=dtype)
    costs[0] = 0
    for probability, mask in zip(probabilities, masks):
        probability = dtype(probability)
        weight = np.log1p(-probability) - np.log(probability)
        permutation = indices ^ mask
        masses = (1 - probability) * masses + probability * masses[permutation]
        costs = np.minimum(costs, weight + costs[permutation])
    if return_all:
        return masses, costs
    selected = [target, target | (1 << detector_count)]
    return masses[selected], costs[selected]


def evaluate(artifact):
    probabilities = artifact["probabilities"]
    target = sum(1 << detector for detector in artifact["syndrome"])
    masks = edge_masks()
    records = []
    for scale in ANCHORS:
        joint, costs = full_state([scale * probability for probability in probabilities], masks, 20, target=target)
        records.append({"scale": scale, "joint_probabilities": joint.tolist(), "class_costs": costs.tolist()})
    physical = 0 if records[10]["class_costs"][0] <= records[10]["class_costs"][1] else 1
    contrary = 1 - physical
    for record in records:
        joint = record["joint_probabilities"]
        costs = record["class_costs"]
        record["syndrome_probability"] = math.fsum(joint)
        record["signed_gap"] = costs[contrary] - costs[physical]
        record["opposite_posterior"] = joint[contrary] / math.fsum(joint)
        record["opposite_log_odds"] = math.log(joint[contrary]) - math.log(joint[physical])
    derivative = 39 / LOWER_SCALE + math.fsum(probability / (1 - UPPER_SCALE * probability) for probability in probabilities)
    radius = max(right - left for left, right in zip(ANCHORS, ANCHORS[1:])) / 2
    allowance = derivative * radius + GUARD
    gap = min(record["signed_gap"] for record in records) - allowance
    log_odds = min(record["opposite_log_odds"] for record in records) - allowance
    posterior = 1 / (1 + math.exp(-log_odds))
    mass = min(record["syndrome_probability"] for record in records) * math.exp(-allowance)
    score = max(0.0, min(gap / GAP_TARGET, log_odds / math.log(POSTERIOR_TARGET / (1 - POSTERIOR_TARGET)), mass / MASS_TARGET))
    failures = []
    if gap < GAP_TARGET:
        failures.append("gap")
    if posterior < POSTERIOR_TARGET:
        failures.append("opposite_posterior")
    if mass < MASS_TARGET:
        failures.append("syndrome_probability")
    worst_scale = max(0.0, min(min(record["signed_gap"] / GAP_TARGET,
        record["opposite_log_odds"] / math.log(POSTERIOR_TARGET / (1 - POSTERIOR_TARGET)),
        record["syndrome_probability"] / MASS_TARGET) for record in records))
    result = {"valid": True, "passed": gap >= GAP_TARGET and posterior >= POSTERIOR_TARGET and mass >= MASS_TARGET,
              "reason": "certified_continuous_entropy_inversion" if not failures else "certified_targets_not_met: " + ", ".join(failures),
              "worst_scale_score": worst_scale, "worst_family_score": score,
              "runtime_score": 1.0, "resource_score": 1.0,
              "core_score": score, "physical_class": physical, "opposite_class": contrary,
              "certified_gap": gap, "certified_opposite_posterior": posterior,
              "certified_opposite_log_odds": log_odds, "certified_syndrome_probability": mass,
              "derivative_bound": derivative, "cover_radius": radius, "allowance": allowance,
              "anchors": records, "oracle": "independent_full_syndrome_logical_dp"}
    if not all(math.isfinite(result[key]) for key in ("core_score", "certified_gap", "certified_opposite_posterior", "certified_syndrome_probability")):
        raise ValueError("nonfinite inference result")
    return result
