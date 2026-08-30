import sys

sys.dont_write_bytecode = True

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np


PRIVATE = Path(__file__).resolve().parent
CONCEPT = PRIVATE.parent
GENERATION = CONCEPT / "generations/generation_2"
TARGETS = {"gap": 0.85, "posterior": 0.845, "mass": 0.0000175}


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def frozen_hashes():
    result = {}
    for label, root in (("generation_1", CONCEPT), ("generation_2", GENERATION)):
        manifest_path = root / "evaluator/hidden/frozen_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for relative, expected in manifest["files_sha256"].items():
            assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
        result[label] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return result


def projection_matrix():
    graph = json.loads((GENERATION / "participant/input/graph.json").read_text())
    projection = np.zeros((39, 20))
    for edge in graph["edges"]:
        projection[edge["id"], edge["detectors"]] = 1 / len(edge["detectors"])
    return projection


def balance(field, rates, projection):
    raw = projection @ np.asarray(field, dtype=float)
    centered = raw - np.dot(rates, raw) / math.fsum(rates)
    denominator = np.max(np.abs(centered))
    if denominator < 1e-14:
        raise ValueError("constant calibration field")
    return centered / denominator


def paths(artifact):
    rates = np.asarray(artifact["probabilities"], dtype=float)
    projection = projection_matrix()
    result = []
    for column in range(4):
        for row in range(3):
            field = [int(column <= detector // 4 <= column + 1 and row <= detector % 4 <= row + 1) for detector in range(20)]
            direction = balance(field, rates, projection)
            for background in (0.95, 1.05):
                result.append({"id": f"patch_2x2/{column},{row}@{background}", "family": "patch_2x2", "background": background,
                               "interval": [-0.05, 0.05], "intercept": background * rates, "slope": background * rates * direction})
    row_modes = {"split": [1, 1, -1, -1], "staggered": [1, -1, 1, -1]}
    column_modes = {"split_after_2": [1, 1, -1, -1, -1], "split_after_3": [1, 1, 1, -1, -1], "staggered": [1, -1, 1, -1, 1]}
    for row_name, row_signs in row_modes.items():
        row_direction = balance([row_signs[detector % 4] for detector in range(20)], rates, projection)
        for column_name, column_signs in column_modes.items():
            column_direction = balance([column_signs[detector // 4] for detector in range(20)], rates, projection)
            for row_sign, column_sign in itertools.product((-1, 1), repeat=2):
                for background in (0.95, 1.05):
                    intercept = background * rates * (1 + 0.05 * row_sign * row_direction)
                    slope = background * rates * 0.05 * (column_sign * column_direction - row_sign * row_direction)
                    result.append({"id": f"row_column_mix/{row_name}/{column_name}/{row_sign},{column_sign}@{background}",
                                   "family": "row_column_mix", "background": background,
                                   "interval": [0.0, 1.0], "intercept": intercept, "slope": slope})
    return result


def derivative_bound(first, second, slope):
    minimum = np.minimum(first, second)
    maximum = np.maximum(first, second)
    if np.any(minimum <= 0) or np.any(maximum >= 0.5):
        raise ValueError("calibration outside positive low-noise domain")
    return math.fsum(abs(value) / (lower * (1 - upper)) for value, lower, upper in zip(slope, minimum, maximum))


def cone_certificate(parameters, observations, intercept, slope):
    guard = 1e-10
    bounds = {"gap": [], "log_odds": [], "log_mass": []}
    interval_derivatives = []
    for index in range(len(parameters) - 1):
        first, second = parameters[index:index + 2]
        derivative = derivative_bound(intercept + first * slope, intercept + second * slope, slope)
        interval_derivatives.append(derivative)
        for metric in bounds:
            left, right = observations[index][metric], observations[index + 1][metric]
            bound = min(left, right, (left + right - derivative * (second - first)) / 2) - guard
            bounds[metric].append(bound)
    gap, log_odds, log_mass = (min(bounds[metric]) for metric in ("gap", "log_odds", "log_mass"))
    return {"gap": gap, "log_odds": log_odds, "posterior": 1 / (1 + math.exp(-log_odds)), "mass": math.exp(log_mass)}, interval_derivatives


def probe_path(path, artifact, physical, checker, anchors):
    parameters = np.linspace(*path["interval"], anchors)
    records = []
    for parameter in parameters:
        rates = path["intercept"] + parameter * path["slope"]
        joint, costs = checker.frontier(rates, artifact["syndrome"])
        mass = float(sum(joint))
        records.append({"parameter": float(parameter), "joint_probabilities": joint.tolist(), "class_costs": costs.tolist(),
                        "gap": float(costs[1 - physical] - costs[physical]), "posterior": float(joint[1 - physical] / mass),
                        "mass": mass, "log_odds": math.log(float(joint[1 - physical] / joint[physical])), "log_mass": math.log(mass)})
    certificate, derivatives = cone_certificate(parameters, records, path["intercept"], path["slope"])
    raw = {metric: min(record[metric] for record in records) for metric in ("gap", "posterior", "mass")}
    actual_failures = [metric for metric in TARGETS if raw[metric] < TARGETS[metric]]
    certificate_failures = [metric for metric in TARGETS if certificate[metric] < TARGETS[metric]]
    target_odds = math.log(TARGETS["posterior"] / (1 - TARGETS["posterior"]))
    score = max(0.0, min(certificate["gap"] / TARGETS["gap"], certificate["log_odds"] / target_odds, certificate["mass"] / TARGETS["mass"]))
    return {"id": path["id"], "family": path["family"], "background": path["background"], "interval": path["interval"],
            "intercept": path["intercept"].tolist(), "slope": path["slope"].tolist(), "anchors": records,
            "interval_derivative_bounds": derivatives, "anchor_minima": raw, "certificate": certificate, "score": score,
            "actual_failures": actual_failures, "certificate_failures": certificate_failures,
            "certificate_only_failure": bool(certificate_failures) and not actual_failures}


def independence(artifact, reports, physical, oracle):
    output = []
    for family in ("patch_2x2", "row_column_mix"):
        subset = [report for report in reports if report["family"] == family]
        for metric in TARGETS:
            worst = min(subset, key=lambda report: report["anchor_minima"][metric])
            anchor = min(worst["anchors"], key=lambda record: record[metric])
            rates = np.array(worst["intercept"]) + anchor["parameter"] * np.array(worst["slope"])
            native = oracle.native_many([rates], oracle.edge_masks(), 20, sum(1 << detector for detector in artifact["syndrome"]))[0]
            np.testing.assert_allclose(native[:2], anchor["joint_probabilities"], rtol=3e-12, atol=0)
            np.testing.assert_allclose(native[2:], anchor["class_costs"], rtol=3e-12, atol=1e-12)
            output.append({"family": family, "metric": metric, "path": worst["id"], "parameter": anchor["parameter"],
                           "joint_probabilities": native[:2].tolist(), "class_costs": native[2:].tolist(),
                           "gap": float(native[3 - physical] - native[2 + physical]),
                           "posterior": float(native[1 - physical] / sum(native[:2])), "mass": float(sum(native[:2])), "passed": True})
    return output


def run(witness, anchors=51):
    started = time.monotonic()
    hashes_before = frozen_hashes()
    oracle = load("extension_native", GENERATION / "evaluator/hidden/oracle.py")
    checker = load("extension_frontier", GENERATION / "participant/workspace/check.py")
    artifact = oracle.read_artifact(witness)
    nominal_costs = checker.frontier(artifact["probabilities"], artifact["syndrome"])[1]
    physical = int(nominal_costs[1] < nominal_costs[0])
    candidates = paths(artifact)
    reports = [probe_path(path, artifact, physical, checker, anchors) for path in candidates]
    families = {}
    for family in ("patch_2x2", "row_column_mix"):
        subset = [report for report in reports if report["family"] == family]
        families[family] = {"paths": len(subset), "inference_points": len(subset) * anchors,
                            "score": min(report["score"] for report in subset),
                            "anchor_minima": {metric: min(report["anchor_minima"][metric] for report in subset) for metric in TARGETS},
                            "certificate_minima": {metric: min(report["certificate"][metric] for report in subset) for metric in TARGETS},
                            "actual_failure_clusters": dict(Counter("+".join(report["actual_failures"]) or "none" for report in subset)),
                            "certificate_failure_clusters": dict(Counter("+".join(report["certificate_failures"]) or "none" for report in subset)),
                            "certificate_only_failures": sum(report["certificate_only_failure"] for report in subset)}
    checks = independence(artifact, reports, physical, oracle)
    original_reports = json.loads((GENERATION / "adversary/known_independent_metrics.json").read_text())
    known_hash = hashlib.sha256((PRIVATE / "known_witness.json").read_bytes()).hexdigest()
    tested_hash = hashlib.sha256(Path(witness).read_bytes()).hexdigest()
    inherited_known_score = original_reports["core_score"] if tested_hash == known_hash else None
    estimated_cpu = original_reports["evaluation_cpu_seconds"] * (2265 + len(reports) * anchors) / 2265
    assert frozen_hashes() == hashes_before
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "state": "private_unfrozen_extension_probe",
            "artifact_sha256": tested_hash, "tested_private_known_only": tested_hash == known_hash,
            "live_attempts_read": False, "generation_3_created": False, "thresholds_changed": False,
            "targets": TARGETS, "inherited_generation_two_known_score": inherited_known_score,
            "domain": {"patch_paths": 24, "mixture_paths": 48, "background_scales": [0.95, 1.05],
                       "maximum_local_rate_change": 0.05, "expected_error_count_preserved": True,
                       "one_dimensional_paths_only": True, "full_mixing_diamond_or_box_claimed": False},
            "anchors_per_path": anchors, "families": families, "independent_checks": checks,
            "extra_inference_points": len(reports) * anchors, "total_with_generation_two": 2265 + len(reports) * anchors,
            "projected_total_native_cpu_seconds": estimated_cpu, "projection_is_not_a_runtime_guarantee": True,
            "frozen_manifests_unchanged": hashes_before, "paths": reports, "elapsed_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness", nargs="?", default=str(PRIVATE / "known_witness.json"))
    parser.add_argument("--output", default=str(PRIVATE / "extension_stress_report.json"))
    arguments = parser.parse_args()
    destination = Path(arguments.output).resolve()
    if not destination.is_relative_to(PRIVATE.resolve()):
        parser.error("outputs must stay under concept_2/adversary")
    report = run(arguments.witness)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "paths"}, indent=2))


if __name__ == "__main__":
    main()
