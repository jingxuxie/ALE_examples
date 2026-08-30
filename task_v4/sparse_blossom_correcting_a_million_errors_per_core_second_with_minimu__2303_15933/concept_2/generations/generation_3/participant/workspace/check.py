import sys

sys.dont_write_bytecode = True

import argparse
from collections import Counter
import importlib.util
import itertools
import json
import math
from pathlib import Path
import resource
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
LOADER = importlib.util.spec_from_file_location("generation_three_inherited", Path(__file__).with_name("inherited.py"))
inherited = importlib.util.module_from_spec(LOADER)
LOADER.loader.exec_module(inherited)
load_submission = inherited.load_submission
validate = inherited.validate
frontier = inherited.frontier


def calibrations(data, spec=None):
    if spec is None:
        spec = json.loads((ROOT / "input/spec.json").read_text())
    groups = inherited.calibrations(data, spec)
    rates = np.asarray(data["probabilities"], dtype=float)
    graph = json.loads((ROOT / "input/graph.json").read_text())
    projection = np.zeros((39, 20))
    for edge in graph["edges"]:
        projection[edge["id"], edge["detectors"]] = 1 / len(edge["detectors"])
    orientation = np.asarray([1] * 24 + [-1] * 15)
    fields = [("orientation", "uniform", np.ones(20))]
    for family, count in (("orientation_rows", 4), ("orientation_columns", 5)):
        for tail in itertools.product((-1, 1), repeat=count - 1):
            signs = [1, *tail]
            if min(signs) == 1:
                continue
            field = [signs[detector % 4 if family == "orientation_rows" else detector // 4] for detector in range(20)]
            fields.append((family, "".join("+" if sign > 0 else "-" for sign in signs), field))
    for row in range(4):
        for column in range(5):
            field = [(1 - 2 * int(detector % 4 == row)) * (1 - 2 * int(detector // 4 == column)) for detector in range(20)]
            fields.append(("orientation_cross", f"{row},{column}", field))
    local = spec["orientation_calibration"]
    parameters = np.asarray(local["anchors"])
    for family, label, field in fields:
        raw = orientation * (projection @ field)
        centered = raw - np.dot(rates, raw) / math.fsum(rates)
        levels = centered / np.max(np.abs(centered))
        for background in local["background_scales"]:
            intercept = background * rates
            slope = intercept * levels
            groups.append({"id": family + ":" + label + f"@{background}", "family": family,
                           "parameters": local["anchors"], "background_scale": background, "levels": levels.tolist(),
                           "intercept": intercept, "slope": slope,
                           "probabilities": intercept[None, :] + parameters[:, None] * slope[None, :],
                           "targets": local["targets"], "certificate": "interval_endpoint_cones"})
    return groups


def summarize_extension(group, values, physical, guard):
    records = []
    for parameter, (joint, costs) in zip(group["parameters"], values):
        total = float(sum(joint))
        records.append({"parameter": parameter, "joint_probabilities": list(map(float, joint)), "class_costs": list(map(float, costs)),
                        "signed_gap": float(costs[1 - physical] - costs[physical]), "opposite_posterior": float(joint[1 - physical] / total),
                        "opposite_log_odds": math.log(float(joint[1 - physical] / joint[physical])), "syndrome_probability": total})
    observations = np.asarray([[record["signed_gap"], record["opposite_log_odds"], math.log(record["syndrome_probability"])] for record in records])
    derivatives = []
    interval_bounds = []
    for index, (left, right) in enumerate(zip(group["parameters"], group["parameters"][1:])):
        first = group["probabilities"][index]
        second = group["probabilities"][index + 1]
        derivative = math.fsum(abs(slope) / (min(first_rate, second_rate) * (1 - max(first_rate, second_rate))) for slope, first_rate, second_rate in zip(group["slope"], first, second))
        derivatives.append(derivative)
        interval_bounds.append(np.minimum(np.minimum(observations[index], observations[index + 1]),
                                          (observations[index] + observations[index + 1] - derivative * (right - left)) / 2) - guard)
    gap, log_odds, log_mass = map(float, np.min(interval_bounds, axis=0))
    posterior = 1 / (1 + math.exp(-log_odds))
    mass = math.exp(log_mass)
    targets = group["targets"]
    failures = [key for key, value in (("gap", gap), ("opposite_posterior", posterior), ("syndrome_probability", mass)) if value < targets[key]]
    point_minima = {"gap": min(record["signed_gap"] for record in records),
                    "opposite_posterior": min(record["opposite_posterior"] for record in records),
                    "syndrome_probability": min(record["syndrome_probability"] for record in records)}
    actual = [key for key, value in point_minima.items() if value < targets[key]]
    target_odds = math.log(targets["opposite_posterior"] / (1 - targets["opposite_posterior"]))
    score = max(0.0, min(gap / targets["gap"], log_odds / target_odds, mass / targets["syndrome_probability"]))
    pointwise = max(0.0, min(min(record["signed_gap"] / targets["gap"], record["opposite_log_odds"] / target_odds, record["syndrome_probability"] / targets["syndrome_probability"]) for record in records))
    return {"id": group["id"], "family": group["family"], "targets": targets, "certified_gap": gap,
            "certified_opposite_log_odds": log_odds, "certified_opposite_posterior": posterior, "certified_syndrome_probability": mass,
            "score": score, "pointwise_score": pointwise, "passed": not failures, "failures": failures, "actual_anchor_failures": actual,
            "certificate_only_failure": bool(failures) and not actual, "anchor_minima": point_minima,
            "certificate": "interval_endpoint_cones", "interval_derivative_bounds": derivatives, "anchors": records}


def combine(reports, physical):
    failures = [report["id"] for report in reports if not report["passed"]]
    extension = reports[45:]
    certificate_fields = ("certified_gap", "certified_opposite_posterior", "certified_syndrome_probability")
    return {"valid": True, "passed": not failures,
            "reason": "certified_spatial_and_orientation_inversion" if not failures else "calibration_targets_not_met",
            "core_score": min(report["score"] for report in reports), "nominal_score": reports[0]["score"],
            "inherited_generation_two_score": min(report["score"] for report in reports[:45]),
            "extension_score": min(report["score"] for report in extension),
            "local_score": min(report["score"] for report in reports[1:]), "worst_family_score": min(report["score"] for report in reports[1:]),
            "worst_scale_score": min(report["pointwise_score"] for report in reports), "runtime_score": 1.0, "resource_score": 1.0,
            "physical_class": physical, "opposite_class": 1 - physical, "failed_groups": failures,
            "extension_minimum_certificates": {key: min(report[key] for report in extension) for key in certificate_fields},
            "extension_point_minima": {key: min(report["anchor_minima"][key] for report in extension) for key in extension[0]["anchor_minima"]},
            "extension_failure_clusters": dict(Counter("+".join(report["failures"]) or "none" for report in extension)),
            "extension_actual_failure_clusters": dict(Counter("+".join(report["actual_anchor_failures"]) or "none" for report in extension)),
            "extension_certificate_only_failures": sum(report["certificate_only_failure"] for report in extension),
            "groups": reports, "inference_points": sum(len(report["anchors"]) for report in reports)}


def check(data):
    validate(data)
    spec = json.loads((ROOT / "input/spec.json").read_text())
    physical_costs = frontier(data["probabilities"], data["syndrome"])[1]
    physical = int(physical_costs[1] < physical_costs[0])
    reports = []
    for group in calibrations(data, spec):
        values = [frontier(probabilities, data["syndrome"]) for probabilities in group["probabilities"]]
        summarize = summarize_extension if group.get("certificate") == "interval_endpoint_cones" else inherited.summarize_group
        reports.append(summarize(group, values, physical, spec["numerical_guard"]))
    return combine(reports, physical)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--output")
    parser.add_argument("--summary-only", action="store_true")
    arguments = parser.parse_args()
    started, cpu_started = time.monotonic(), time.process_time()
    try:
        result = check(load_submission(arguments.submission))
    except (ValueError, UnicodeError, OSError, OverflowError, RecursionError) as error:
        result = {"valid": False, "passed": False, "reason": "invalid_submission: " + str(error), "core_score": 0.0,
                  "worst_family_score": 0.0, "worst_scale_score": 0.0, "runtime_score": 0.0, "resource_score": 0.0}
    result["evaluation_seconds"] = time.monotonic() - started
    result["evaluation_cpu_seconds"] = time.process_time() - cpu_started
    result["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    if arguments.output:
        Path(arguments.output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if arguments.summary_only:
        result = {key: value for key, value in result.items() if key != "groups"}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
