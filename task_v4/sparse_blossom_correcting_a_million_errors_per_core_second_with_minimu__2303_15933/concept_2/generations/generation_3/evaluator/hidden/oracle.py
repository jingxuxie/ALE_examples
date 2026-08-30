import sys

sys.dont_write_bytecode = True

from collections import Counter
import importlib.util
import math
from pathlib import Path

import numpy as np


LOADER = importlib.util.spec_from_file_location("generation_three_trusted_inherited", Path(__file__).with_name("inherited_oracle.py"))
inherited = importlib.util.module_from_spec(LOADER)
LOADER.loader.exec_module(inherited)
read_artifact = inherited.read_artifact
edge_masks = inherited.edge_masks
native_many = inherited.native_many
full_state = inherited.full_state
TARGETS = {"gap": 0.85, "opposite_posterior": 0.845, "syndrome_probability": 0.0000175}


def schedule(probabilities):
    rates = np.asarray(probabilities, dtype=float)
    groups = inherited.schedule(probabilities)
    fields = [("orientation", "uniform", [1] * 20)]
    for family, count in (("orientation_rows", 4), ("orientation_columns", 5)):
        for pattern in range((1 << (count - 1)) - 1):
            signs = [1] + [1 if pattern & (1 << (count - 2 - index)) else -1 for index in range(count - 1)]
            field = [signs[detector % 4 if count == 4 else detector // 4] for detector in range(20)]
            fields.append((family, "".join("+" if value == 1 else "-" for value in signs), field))
    for row in range(4):
        for column in range(5):
            field = [-1 if ((detector % 4 == row) != (detector // 4 == column)) else 1 for detector in range(20)]
            fields.append(("orientation_cross", str(row) + "," + str(column), field))
    for family, label, field in fields:
        raw = []
        for cut in range(6):
            for row in range(4):
                if cut == 0:
                    value = field[row]
                elif cut == 5:
                    value = field[16 + row]
                else:
                    value = (field[4 * (cut - 1) + row] + field[4 * cut + row]) / 2
                raw.append(value)
        for column in range(5):
            for row in range(3):
                raw.append(-(field[4 * column + row] + field[4 * column + row + 1]) / 2)
        average = math.fsum(rate * level for rate, level in zip(rates, raw)) / math.fsum(rates)
        centered = [value - average for value in raw]
        magnitude = max(map(abs, centered))
        levels = [value / magnitude for value in centered]
        parameters = [round(-0.05 + 0.0025 * index, 6) for index in range(41)]
        for background in (0.95, 1.05):
            velocity = np.asarray([background * rate * level for rate, level in zip(rates, levels)])
            origin = background * rates
            matrix = np.asarray([origin + parameter * velocity for parameter in parameters])
            groups.append({"id": family + ":" + label + f"@{background}", "family": family,
                           "parameters": parameters, "rates": matrix, "velocity": velocity,
                           "targets": TARGETS, "certificate": "interval_endpoint_cones"})
    return groups


def extension_report(group, values, physical):
    records = []
    contrary = 1 - physical
    for parameter, result in zip(group["parameters"], values):
        mass = float(result[0] + result[1])
        records.append({"parameter": parameter, "joint_probabilities": [float(result[0]), float(result[1])],
                        "class_costs": [float(result[2]), float(result[3])], "signed_gap": float(result[2 + contrary] - result[2 + physical]),
                        "opposite_posterior": float(result[contrary] / mass), "opposite_log_odds": math.log(float(result[contrary] / result[physical])),
                        "syndrome_probability": mass})
    minimum_bounds = [math.inf, math.inf, math.inf]
    derivatives = []
    for position in range(len(records) - 1):
        derivative = 0.0
        for edge, velocity in enumerate(group["velocity"]):
            first, second = group["rates"][position:position + 2, edge]
            derivative += abs(velocity) / (min(first, second) * (1 - max(first, second)))
        derivatives.append(float(derivative))
        length = group["parameters"][position + 1] - group["parameters"][position]
        for metric, key in enumerate(("signed_gap", "opposite_log_odds", "syndrome_probability")):
            first, second = records[position][key], records[position + 1][key]
            if key == "syndrome_probability":
                first, second = math.log(first), math.log(second)
            lower = min(first, second, 0.5 * (first + second - derivative * length)) - 1e-10
            minimum_bounds[metric] = min(minimum_bounds[metric], lower)
    gap, odds, log_mass = minimum_bounds
    posterior, mass = 1 / (1 + math.exp(-odds)), math.exp(log_mass)
    anchor_minima = {"gap": min(record["signed_gap"] for record in records),
                     "opposite_posterior": min(record["opposite_posterior"] for record in records),
                     "syndrome_probability": min(record["syndrome_probability"] for record in records)}
    actual = [key for key in TARGETS if anchor_minima[key] < TARGETS[key]]
    failures = [key for key, value in (("gap", gap), ("opposite_posterior", posterior), ("syndrome_probability", mass)) if value < TARGETS[key]]
    target_odds = math.log(TARGETS["opposite_posterior"] / (1 - TARGETS["opposite_posterior"]))
    score = max(0.0, min(gap / TARGETS["gap"], odds / target_odds, mass / TARGETS["syndrome_probability"]))
    pointwise = max(0.0, min(min(record["signed_gap"] / TARGETS["gap"], record["opposite_log_odds"] / target_odds, record["syndrome_probability"] / TARGETS["syndrome_probability"]) for record in records))
    return {"id": group["id"], "family": group["family"], "targets": TARGETS, "certified_gap": gap,
            "certified_opposite_log_odds": odds, "certified_opposite_posterior": posterior, "certified_syndrome_probability": mass,
            "score": score, "pointwise_score": pointwise, "passed": not failures, "failures": failures, "actual_anchor_failures": actual,
            "certificate_only_failure": bool(failures) and not actual, "anchor_minima": anchor_minima,
            "certificate": "interval_endpoint_cones", "interval_derivative_bounds": derivatives, "anchors": records}


def evaluate(artifact):
    groups = schedule(artifact["probabilities"])
    matrix = np.concatenate([group["rates"] for group in groups])
    target = sum(1 << detector for detector in artifact["syndrome"])
    values = native_many(matrix, edge_masks(), 20, target)
    if not np.all(np.isfinite(values)) or not np.all(values[:, :2] > 0):
        raise RuntimeError("nonfinite or nonpositive trusted inference")
    physical = int(values[10, 3] < values[10, 2])
    reports = []
    offset = 0
    for group in groups:
        count = len(group["parameters"])
        summarize = extension_report if group.get("certificate") == "interval_endpoint_cones" else inherited.group_report
        reports.append(summarize(group, values[offset:offset + count], physical))
        offset += count
    extension = reports[45:]
    failed = [report["id"] for report in reports if report["failures"]]
    return {"valid": True, "passed": not failed,
            "reason": "certified_spatial_and_orientation_inversion" if not failed else "calibration_targets_not_met",
            "core_score": min(report["score"] for report in reports), "nominal_score": reports[0]["score"],
            "inherited_generation_two_score": min(report["score"] for report in reports[:45]),
            "extension_score": min(report["score"] for report in extension),
            "local_score": min(report["score"] for report in reports[1:]), "worst_family_score": min(report["score"] for report in reports[1:]),
            "worst_scale_score": min(report["pointwise_score"] for report in reports), "runtime_score": 1.0, "resource_score": 1.0,
            "physical_class": physical, "opposite_class": 1 - physical, "failed_groups": failed,
            "extension_minimum_certificates": {key: min(report[key] for report in extension) for key in ("certified_gap", "certified_opposite_posterior", "certified_syndrome_probability")},
            "extension_point_minima": {key: min(report["anchor_minima"][key] for report in extension) for key in TARGETS},
            "extension_failure_clusters": dict(Counter("+".join(report["failures"]) or "none" for report in extension)),
            "extension_actual_failure_clusters": dict(Counter("+".join(report["actual_anchor_failures"]) or "none" for report in extension)),
            "extension_certificate_only_failures": sum(report["certificate_only_failure"] for report in extension),
            "groups": reports, "inference_points": len(matrix),
            "oracle": "generic_full_state_positive_and_min_plus_dp_with_invertible_binary_basis"}
