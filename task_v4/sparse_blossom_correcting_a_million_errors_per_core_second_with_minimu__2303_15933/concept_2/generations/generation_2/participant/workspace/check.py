import sys

sys.dont_write_bytecode = True

import argparse
from collections import Counter
import importlib.util
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
LOADER = importlib.util.spec_from_file_location("generation_two_public_core", Path(__file__).with_name("core.py"))
core = importlib.util.module_from_spec(LOADER)
LOADER.loader.exec_module(core)
load_submission = core.load_submission
validate = core.validate
frontier = core.frontier


def calibrations(data, spec=None):
    if spec is None:
        spec = json.loads((ROOT / "input/spec.json").read_text())
    rates = np.array(data["probabilities"], dtype=float)
    graph = json.loads((ROOT / "input/graph.json").read_text())
    projection = np.zeros((39, 20))
    for edge in graph["edges"]:
        projection[edge["id"], edge["detectors"]] = 1 / len(edge["detectors"])
    lower, upper = spec["scale_interval"]
    global_bound = 39 / lower + math.fsum(rate / (1 - upper * rate) for rate in rates)
    groups = [{"id": "global", "family": "global", "parameters": spec["anchors"],
               "probabilities": np.array(spec["anchors"])[:, None] * rates,
               "derivative_bound": global_bound, "targets": spec["targets"]}]
    local = spec["local_calibration"]
    amplitude = max(abs(value) for value in local["amplitude_interval"])
    for family, count in (("rows", 4), ("columns", 5)):
        for tail in itertools.product((-1, 1), repeat=count - 1):
            signs = [1, *tail]
            if min(signs) == 1:
                continue
            field = [signs[detector % 4 if family == "rows" else detector // 4] for detector in range(20)]
            raw = projection @ field
            centered = raw - np.dot(rates, raw) / math.fsum(rates)
            levels = centered / np.max(np.abs(centered))
            for background in local["background_scales"]:
                bound = math.fsum(abs(level) / ((1 - amplitude * abs(level)) * (1 - background * rate * (1 + amplitude * abs(level)))) for level, rate in zip(levels, rates))
                parameters = np.array(local["anchors"])
                groups.append({"id": family + ":" + "".join("+" if sign > 0 else "-" for sign in signs) + f"@{background}",
                               "family": family, "signs": signs, "background_scale": background,
                               "levels": levels.tolist(), "parameters": local["anchors"],
                               "probabilities": background * rates[None, :] * (1 + parameters[:, None] * levels),
                               "derivative_bound": bound, "targets": local["targets"]})
    return groups


def summarize_group(group, results, physical, guard):
    contrary = 1 - physical
    anchors = []
    for parameter, (joint, costs) in zip(group["parameters"], results):
        total = float(sum(joint))
        anchors.append({"parameter": parameter, "joint_probabilities": list(map(float, joint)), "class_costs": list(map(float, costs)),
                        "signed_gap": float(costs[contrary] - costs[physical]), "opposite_posterior": float(joint[contrary] / total),
                        "opposite_log_odds": math.log(float(joint[contrary] / joint[physical])), "syndrome_probability": total})
    radius = max(second - first for first, second in zip(group["parameters"], group["parameters"][1:])) / 2
    allowance = group["derivative_bound"] * radius + guard
    gap = min(anchor["signed_gap"] for anchor in anchors) - allowance
    odds = min(anchor["opposite_log_odds"] for anchor in anchors) - allowance
    posterior = 1 / (1 + math.exp(-odds))
    mass = min(anchor["syndrome_probability"] for anchor in anchors) * math.exp(-allowance)
    target = group["targets"]
    target_odds = math.log(target["opposite_posterior"] / (1 - target["opposite_posterior"]))
    failures = [name for name, actual in (("gap", gap), ("opposite_posterior", posterior), ("syndrome_probability", mass)) if actual < target[name]]
    actual_failures = [name for name, actual in (("gap", min(anchor["signed_gap"] for anchor in anchors)), ("opposite_posterior", min(anchor["opposite_posterior"] for anchor in anchors)), ("syndrome_probability", min(anchor["syndrome_probability"] for anchor in anchors))) if actual < target[name]]
    score = max(0.0, min(gap / target["gap"], odds / target_odds, mass / target["syndrome_probability"]))
    pointwise = max(0.0, min(min(anchor["signed_gap"] / target["gap"], anchor["opposite_log_odds"] / target_odds, anchor["syndrome_probability"] / target["syndrome_probability"]) for anchor in anchors))
    return {"id": group["id"], "family": group["family"], "targets": target, "certified_gap": gap,
            "certified_opposite_posterior": posterior, "certified_opposite_log_odds": odds,
            "certified_syndrome_probability": mass, "score": score, "pointwise_score": pointwise,
            "failures": failures, "actual_anchor_failures": actual_failures, "passed": not failures,
            "derivative_bound": group["derivative_bound"], "cover_radius": radius, "allowance": allowance, "anchors": anchors}


def check(data):
    validate(data)
    spec = json.loads((ROOT / "input/spec.json").read_text())
    groups = calibrations(data, spec)
    physical_cost = frontier(data["probabilities"], data["syndrome"])[1]
    physical = int(physical_cost[1] < physical_cost[0])
    reports = []
    for group in groups:
        results = [frontier(rates, data["syndrome"]) for rates in group["probabilities"]]
        reports.append(summarize_group(group, results, physical, spec["numerical_guard"]))
    local = reports[1:]
    failures = [report["id"] for report in reports if not report["passed"]]
    return {"valid": True, "passed": not failures, "reason": "certified_global_and_local_inversion" if not failures else "calibration_targets_not_met",
            "core_score": min(report["score"] for report in reports), "nominal_score": reports[0]["score"],
            "local_score": min(report["score"] for report in local), "worst_family_score": min(report["score"] for report in local),
            "worst_scale_score": min(report["pointwise_score"] for report in reports), "runtime_score": 1.0, "resource_score": 1.0,
            "physical_class": physical, "opposite_class": 1 - physical, "failed_groups": failures,
            "local_minimum_certificates": {field: min(report[field] for report in local) for field in ("certified_gap", "certified_opposite_posterior", "certified_syndrome_probability")},
            "local_failure_clusters": dict(Counter("+".join(report["failures"]) or "none" for report in local)),
            "local_actual_failure_clusters": dict(Counter("+".join(report["actual_anchor_failures"]) or "none" for report in local)),
            "groups": reports, "inference_points": sum(len(report["anchors"]) for report in reports)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--output")
    parser.add_argument("--summary-only", action="store_true")
    arguments = parser.parse_args()
    started = time.monotonic()
    try:
        result = check(load_submission(arguments.submission))
    except (ValueError, UnicodeError, OSError, OverflowError, RecursionError) as error:
        result = {"valid": False, "passed": False, "reason": "invalid_submission: " + str(error), "core_score": 0.0,
                  "worst_family_score": 0.0, "worst_scale_score": 0.0, "runtime_score": 0.0, "resource_score": 0.0}
    result["evaluation_seconds"] = time.monotonic() - started
    if arguments.output:
        Path(arguments.output).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if arguments.summary_only:
        result = {key: value for key, value in result.items() if key != "groups"}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
