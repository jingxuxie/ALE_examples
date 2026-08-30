import json
import math
import os
from pathlib import Path
import stat
import ctypes
from collections import Counter

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


def native_many(probabilities, masks, detector_count, target):
    matrix = np.ascontiguousarray(probabilities, dtype=np.float64)
    masks = np.ascontiguousarray(masks, dtype=np.uint32)
    if matrix.ndim != 2 or matrix.shape[1] != len(masks):
        raise ValueError("incorrect trusted inference shape")
    output = np.empty((len(matrix), 4), dtype=np.float64)
    library = ctypes.CDLL(str(Path(__file__).with_name("full_state.so")))
    pointer = ctypes.POINTER(ctypes.c_double)
    library.infer_many.argtypes = [pointer, ctypes.POINTER(ctypes.c_uint), ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, pointer]
    library.infer_many.restype = ctypes.c_int
    code = library.infer_many(matrix.ctypes.data_as(pointer), masks.ctypes.data_as(ctypes.POINTER(ctypes.c_uint)), len(masks), detector_count, target, len(matrix), output.ctypes.data_as(pointer))
    if code:
        raise RuntimeError("trusted native inference failed: " + str(code))
    return output


def schedule(probabilities):
    rates = np.array(probabilities, dtype=float)
    global_parameters = [round(0.95 + 0.005 * index, 6) for index in range(21)]
    global_derivative = 39 / 0.95 + math.fsum(rate / (1 - 1.05 * rate) for rate in rates)
    groups = [{"id": "global", "family": "global", "parameters": global_parameters,
               "rates": np.array([rates * value for value in global_parameters]), "derivative": global_derivative,
               "targets": {"gap": 1.08, "opposite_posterior": 0.85, "syndrome_probability": 0.0000175}}]
    parameters = [round(-0.05 + 0.002 * index, 6) for index in range(51)]
    for family, width in (("rows", 4), ("columns", 5)):
        for pattern in range((1 << (width - 1)) - 1):
            signs = [1] + [1 if (pattern >> (width - 2 - position)) & 1 else -1 for position in range(width - 1)]
            raw = []
            for cut in range(6):
                for row in range(4):
                    if family == "rows":
                        value = signs[row]
                    elif cut == 0:
                        value = signs[0]
                    elif cut == 5:
                        value = signs[4]
                    else:
                        value = (signs[cut - 1] + signs[cut]) / 2
                    raw.append(value)
            for column in range(5):
                for row in range(3):
                    raw.append((signs[row] + signs[row + 1]) / 2 if family == "rows" else signs[column])
            average = math.fsum(rate * value for rate, value in zip(rates, raw)) / math.fsum(rates)
            centered = [value - average for value in raw]
            magnitude = max(abs(value) for value in centered)
            levels = np.array([value / magnitude for value in centered])
            for background in (0.95, 1.05):
                derivative = 0.0
                for rate, level in zip(rates, levels):
                    magnitude = abs(level)
                    derivative += magnitude / ((1 - 0.05 * magnitude) * (1 - background * rate * (1 + 0.05 * magnitude)))
                groups.append({"id": family + ":" + "".join("+" if sign > 0 else "-" for sign in signs) + f"@{background}",
                               "family": family, "parameters": parameters, "rates": np.array([background * rates * (1 + value * levels) for value in parameters]),
                               "derivative": derivative,
                               "targets": {"gap": 0.85, "opposite_posterior": 0.845, "syndrome_probability": 0.0000175}})
    return groups


def group_report(group, values, physical):
    opposite = 1 - physical
    records = []
    for parameter, row in zip(group["parameters"], values):
        total = float(row[0] + row[1])
        records.append({"parameter": parameter, "joint_probabilities": row[:2].tolist(), "class_costs": row[2:].tolist(),
                        "signed_gap": float(row[2 + opposite] - row[2 + physical]), "opposite_posterior": float(row[opposite] / total),
                        "opposite_log_odds": math.log(float(row[opposite])) - math.log(float(row[physical])), "syndrome_probability": total})
    radius = max(group["parameters"][index + 1] - group["parameters"][index] for index in range(len(records) - 1)) / 2
    allowance = group["derivative"] * radius + 1e-10
    gap = min(record["signed_gap"] for record in records) - allowance
    log_odds = min(record["opposite_log_odds"] for record in records) - allowance
    posterior = 1 / (1 + math.exp(-log_odds))
    mass = min(record["syndrome_probability"] for record in records) * math.exp(-allowance)
    targets = group["targets"]
    failures = []
    if gap < targets["gap"]:
        failures.append("gap")
    if posterior < targets["opposite_posterior"]:
        failures.append("opposite_posterior")
    if mass < targets["syndrome_probability"]:
        failures.append("syndrome_probability")
    actual = []
    for metric, field in (("gap", "signed_gap"), ("opposite_posterior", "opposite_posterior"), ("syndrome_probability", "syndrome_probability")):
        if min(record[field] for record in records) < targets[metric]:
            actual.append(metric)
    target_odds = math.log(targets["opposite_posterior"] / (1 - targets["opposite_posterior"]))
    score = max(0.0, min(gap / targets["gap"], log_odds / target_odds, mass / targets["syndrome_probability"]))
    pointwise = max(0.0, min(min(record["signed_gap"] / targets["gap"], record["opposite_log_odds"] / target_odds, record["syndrome_probability"] / targets["syndrome_probability"]) for record in records))
    return {"id": group["id"], "family": group["family"], "targets": targets, "certified_gap": gap,
            "certified_opposite_posterior": posterior, "certified_opposite_log_odds": log_odds,
            "certified_syndrome_probability": mass, "score": score, "pointwise_score": pointwise,
            "failures": failures, "actual_anchor_failures": actual, "passed": not failures,
            "derivative_bound": group["derivative"], "cover_radius": radius, "allowance": allowance, "anchors": records}


def evaluate(artifact):
    groups = schedule(artifact["probabilities"])
    probabilities = np.concatenate([group["rates"] for group in groups])
    target = sum(1 << detector for detector in artifact["syndrome"])
    values = native_many(probabilities, edge_masks(), 20, target)
    if not np.all(np.isfinite(values)) or not np.all(values[:, :2] > 0):
        raise RuntimeError("nonfinite or nonpositive trusted inference")
    physical = int(values[10, 3] < values[10, 2])
    reports = []
    offset = 0
    for group in groups:
        count = len(group["parameters"])
        reports.append(group_report(group, values[offset:offset + count], physical))
        offset += count
    failed = [report["id"] for report in reports if report["failures"]]
    local = reports[1:]
    return {"valid": True, "passed": not failed, "reason": "certified_global_and_local_inversion" if not failed else "calibration_targets_not_met",
            "core_score": min(report["score"] for report in reports), "nominal_score": reports[0]["score"],
            "local_score": min(report["score"] for report in local), "worst_family_score": min(report["score"] for report in local),
            "worst_scale_score": min(report["pointwise_score"] for report in reports), "runtime_score": 1.0, "resource_score": 1.0,
            "physical_class": physical, "opposite_class": 1 - physical, "failed_groups": failed,
            "local_minimum_certificates": {field: min(report[field] for report in local) for field in ("certified_gap", "certified_opposite_posterior", "certified_syndrome_probability")},
            "local_failure_clusters": dict(Counter("+".join(report["failures"]) or "none" for report in local)),
            "local_actual_failure_clusters": dict(Counter("+".join(report["actual_anchor_failures"]) or "none" for report in local)),
            "groups": reports, "inference_points": offset, "oracle": "generic_full_state_positive_and_min_plus_dp_with_invertible_binary_basis"}

