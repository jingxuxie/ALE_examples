import sys

sys.dont_write_bytecode = True

from collections import Counter
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
CONCEPT = ROOT.parents[1]


def load(name, source):
    specification = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def frozen_controls():
    output = {}
    for name, root in (("generation_1", CONCEPT), ("generation_2", CONCEPT / "generations/generation_2")):
        path = root / "evaluator/hidden/frozen_manifest.json"
        report = json.loads(path.read_text())
        for relative, expected in report["files_sha256"].items():
            assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
        output[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return output


def malformed_controls(public, oracle, artifact):
    destination = ROOT / "adversary/audit_cases"
    destination.mkdir(exist_ok=True)
    cases = {}

    def changed(key, value):
        return {**artifact, key: value}

    cases["array"] = []
    cases["null"] = None
    cases["extra_key"] = {**artifact, "extra": 1}
    cases["missing_key"] = {key: value for key, value in artifact.items() if key != "version"}
    for value in (True, 1.0, 2, "1"):
        cases["version_" + repr(value)] = changed("version", value)
    cases["short_rates"] = changed("probabilities", artifact["probabilities"][:-1])
    cases["long_rates"] = changed("probabilities", artifact["probabilities"] + [0.03])
    for label, value in (("bool", True), ("null", None), ("string", "0.1"), ("nan", math.nan), ("infinity", math.inf),
                         ("negative_infinity", -math.inf), ("negative", -0.01), ("low", 0.019), ("high", 0.141)):
        cases["rate_" + label] = changed("probabilities", [value] + artifact["probabilities"][1:])
    cases["mean"] = changed("probabilities", [0.1] * 39)
    cases["dispersion"] = changed("probabilities", [0.08] * 39)
    for label, value in (("short", [0, 5]), ("long", [0, 1, 2, 4, 5, 8, 9]), ("duplicate", [0, 0, 5, 17]),
                         ("unsorted", [17, 5, 2, 0]), ("float", [0, 2, 5.0, 17]), ("bool", [False, 2, 5, 17]),
                         ("low", [-1, 2, 5, 17]), ("high", [0, 2, 5, 20]), ("rows", [0, 4, 8]), ("columns", [0, 1, 2])):
        cases["syndrome_" + label] = changed("syndrome", value)
    files = []
    for index, (name, contents) in enumerate(cases.items()):
        path = destination / f"{index:02d}_{name}.json"
        path.write_text(json.dumps(contents))
        files.append(path)
    raw_cases = {"utf8": b"\xff\xfe", "oversized": b" " * 16385,
                 "duplicate_key": json.dumps(artifact).replace('"version": 1', '"version": 1, "version": 1').encode(),
                 "overflow": json.dumps(artifact).replace(str(artifact["probabilities"][0]), "1e999", 1).encode(),
                 "trailing": json.dumps(artifact).encode() + b"x", "deep": b"[" * 1100 + b"]" * 1100}
    for name, contents in raw_cases.items():
        path = destination / (name + ".json")
        path.write_bytes(contents)
        files.append(path)
    link = destination / "symlink.json"
    if not link.is_symlink():
        link.symlink_to(ROOT / "participant/baseline/champion.json")
    fifo = destination / "fifo.json"
    if not fifo.exists():
        os.mkfifo(fifo)
    files.extend([link, fifo, destination])
    for path in files:
        for checker in (lambda source: public.validate(public.load_submission(source)), oracle.read_artifact):
            try:
                checker(path)
            except (ValueError, UnicodeError, OSError, OverflowError, RecursionError):
                pass
            else:
                raise AssertionError("malformed artifact accepted: " + str(path))
    cli_count = 0
    for relative in ("participant/workspace/check.py", "evaluator/evaluate.py"):
        for path in (destination / "utf8.json", destination / "oversized.json", fifo):
            result = subprocess.run([sys.executable, "-B", str(ROOT / relative), str(path), "--summary-only"], capture_output=True, text=True, check=True)
            record = json.loads(result.stdout)
            assert record["valid"] is False and record["passed"] is False
            assert record["core_score"] == 0 and record["reason"].startswith("invalid_submission:")
            cli_count += 1
    return {"malformed_files": len(files), "validators_per_file": 2, "cli_cases": cli_count}


def main():
    started = time.monotonic()
    original_hashes = frozen_controls()
    public = load("generation_three_audit_public", ROOT / "participant/workspace/check.py")
    oracle = load("generation_three_audit_oracle", ROOT / "evaluator/hidden/oracle.py")
    artifact_path = ROOT / "participant/baseline/champion.json"
    artifact = oracle.read_artifact(artifact_path)
    assert artifact_path.read_bytes() == (CONCEPT / "champions/generation_2/witness.json").read_bytes()
    assert (ROOT / "evaluator/hidden/full_state.cpp").read_bytes() == (CONCEPT / "generations/generation_2/evaluator/hidden/full_state.cpp").read_bytes()
    groups = public.calibrations(artifact)
    trusted_groups = oracle.schedule(artifact["probabilities"])
    assert len(groups) == len(trusted_groups) == 131
    assert sum(len(group["parameters"]) for group in groups) == 5791
    rates = np.asarray(artifact["probabilities"])
    maximum_schedule_error = 0.0
    for group, trusted in zip(groups, trusted_groups):
        assert group["id"] == trusted["id"]
        maximum_schedule_error = max(maximum_schedule_error, float(np.max(np.abs(group["probabilities"] - trusted["rates"]))))
        np.testing.assert_allclose(group["probabilities"], trusted["rates"], rtol=0, atol=2e-16)
        if group["family"] != "global":
            background = group["background_scale"]
            assert np.max(np.abs(group["probabilities"] / (background * rates) - 1)) <= 0.05 + 2e-15
            np.testing.assert_allclose(group["probabilities"].sum(axis=1), background * sum(rates), rtol=0, atol=3e-15)
    public_report = public.check(artifact)
    (ROOT / "adversary/baseline_public_metrics.json").write_text(json.dumps(public_report, indent=2, allow_nan=False) + "\n")
    physical = public_report["physical_class"]
    off_anchor_count = 0
    native_controls = []
    for path_index, group in enumerate(groups[45:]):
        interval = (17 * path_index + 11) % 40
        left, right = group["parameters"][interval:interval + 2]
        endpoints = group["probabilities"][interval:interval + 2]
        derivative = math.fsum(abs(slope) / (min(first, second) * (1 - max(first, second))) for slope, first, second in zip(group["slope"], *endpoints))
        observations = []
        for fraction in (0.17, 0.5, 0.83):
            parameter = left + fraction * (right - left)
            calibrated = group["intercept"] + parameter * group["slope"]
            joint, costs = public.frontier(calibrated, artifact["syndrome"])
            observation = np.asarray([costs[1 - physical] - costs[physical], math.log(joint[1 - physical] / joint[physical]), math.log(sum(joint))])
            records = public_report["groups"][45 + path_index]["anchors"][interval:interval + 2]
            endpoint_values = np.asarray([[record["signed_gap"], record["opposite_log_odds"], math.log(record["syndrome_probability"])] for record in records])
            cone = np.minimum(np.min(endpoint_values, axis=0), (endpoint_values.sum(axis=0) - derivative * (right - left)) / 2) - 1e-10
            assert np.all(observation >= cone - 2e-12)
            direct_slope_width = float(np.sum(np.abs(group["slope"]) / (calibrated * (1 - calibrated))))
            assert direct_slope_width <= derivative + 2e-12
            observations.append(observation)
            off_anchor_count += 1
            if path_index % 17 == 0 and fraction == 0.5:
                native_controls.append((calibrated, joint, costs))
        for first, second in zip(observations, observations[1:]):
            assert np.all(np.abs(first - second) <= derivative * 0.33 * (right - left) + 2e-11)
    graph = json.loads((ROOT / "participant/input/graph.json").read_text())
    edge_lookup = {tuple(sorted(edge["detectors"])): edge["id"] for edge in graph["edges"]}
    reflection_count = 0
    for reflect_rows, reflect_columns in ((True, False), (False, True), (True, True)):
        def transform(detector):
            column, row = divmod(detector, 4)
            return 4 * (4 - column if reflect_columns else column) + (3 - row if reflect_rows else row)
        permutation = [edge_lookup[tuple(sorted(transform(detector) for detector in edge["detectors"]))] for edge in graph["edges"]]
        reflected_rates = np.empty(39)
        reflected_rates[permutation] = rates
        reflected = {**artifact, "probabilities": reflected_rates.tolist(), "syndrome": sorted(transform(detector) for detector in artifact["syndrome"])}
        reflected_groups = public.calibrations(reflected)[45:]
        for group in groups[45::2]:
            expected = np.empty(39)
            expected[permutation] = group["levels"]
            candidates = [np.asarray(candidate["levels"]) for candidate in reflected_groups if candidate["family"] == group["family"]]
            difference = min(min(np.max(np.abs(candidate - expected)), np.max(np.abs(candidate + expected))) for candidate in candidates)
            assert difference < 2e-12
            reflection_count += 1
        before = public.frontier(rates, artifact["syndrome"])
        after = public.frontier(reflected_rates, reflected["syndrome"])
        logical_flip = (len(artifact["syndrome"]) % 2) if reflect_columns else 0
        for first, second in zip(before, after):
            np.testing.assert_allclose(first, second[::-1] if logical_flip else second, rtol=2e-12, atol=1e-13)
    target = sum(1 << detector for detector in artifact["syndrome"])
    native = oracle.native_many([entry[0] for entry in native_controls], oracle.edge_masks(), 20, target)
    for result, (_, joint, costs) in zip(native, native_controls):
        np.testing.assert_allclose(result[:2], joint, rtol=3e-12, atol=0)
        np.testing.assert_allclose(result[2:], costs, rtol=3e-12, atol=1e-12)
    calibrated, joint, costs = native_controls[-1]
    generic = oracle.full_state(calibrated, oracle.edge_masks(), 20, target=target)
    np.testing.assert_allclose(generic[0], joint, rtol=3e-12, atol=0)
    np.testing.assert_allclose(generic[1], costs, rtol=3e-12, atol=1e-12)
    rng = np.random.default_rng(3108)
    for _ in range(3):
        permutation = rng.permutation(39)
        result = oracle.native_many([calibrated[permutation]], np.asarray(oracle.edge_masks())[permutation], 20, target)[0]
        np.testing.assert_allclose(result[:2], joint, rtol=3e-12, atol=0)
        np.testing.assert_allclose(result[2:], costs, rtol=3e-12, atol=1e-12)
    validation = malformed_controls(public, oracle, artifact)
    independent = json.loads((ROOT / "adversary/baseline_independent_metrics.json").read_text())
    assert independent["valid"] and not independent["passed"]
    assert independent["inference_points"] == 5791
    assert independent["inherited_generation_two_score"] > 1
    assert independent["extension_point_minima"]["gap"] < 0.85
    assert independent["extension_point_minima"]["opposite_posterior"] < 0.845
    comparisons = 0
    max_joint_relative_error, max_cost_absolute_error = 0.0, 0.0
    for expected_group, actual_group in zip(public_report["groups"], independent["groups"]):
        assert expected_group["id"] == actual_group["id"]
        for key in ("score", "certified_gap", "certified_opposite_log_odds", "certified_syndrome_probability"):
            np.testing.assert_allclose(expected_group[key], actual_group[key], rtol=3e-12, atol=1e-13)
        for expected, actual in zip(expected_group["anchors"], actual_group["anchors"]):
            expected_joint = np.asarray(expected["joint_probabilities"])
            actual_joint = np.asarray(actual["joint_probabilities"])
            max_joint_relative_error = max(max_joint_relative_error, float(np.max(np.abs(actual_joint / expected_joint - 1))))
            max_cost_absolute_error = max(max_cost_absolute_error, float(np.max(np.abs(np.asarray(actual["class_costs"]) - expected["class_costs"]))))
            np.testing.assert_allclose(actual_joint, expected_joint, rtol=3e-12, atol=0)
            np.testing.assert_allclose(actual["class_costs"], expected["class_costs"], rtol=3e-12, atol=1e-12)
            comparisons += 1
    assert comparisons == 5791
    assert original_hashes == frozen_controls()
    output = {"passed": True, "known_feasible": False, "solvability": "open_unknown_achievability",
              "full_state_frontier_anchor_comparisons": comparisons, "maximum_joint_relative_error": max_joint_relative_error,
              "maximum_cost_absolute_error": max_cost_absolute_error, "maximum_schedule_absolute_error": maximum_schedule_error,
              "off_anchor_certificate_checks": off_anchor_count, "native_off_anchor_checks": len(native_controls),
              "slow_generic_numpy_full_state_checks": 1, "edge_order_controls": 3, "reflection_domain_controls": reflection_count,
              "reflection_inference_controls": 3, "rate_budget_and_cap_paths": 130, "validation": validation,
              "prior_frozen_manifests_unchanged": original_hashes, "baseline_core_score": independent["core_score"],
              "baseline_actual_failure_clusters": independent["extension_actual_failure_clusters"],
              "baseline_certificate_only_failures": independent["extension_certificate_only_failures"],
              "elapsed_seconds": time.monotonic() - started}
    (ROOT / "adversary/audit_report.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
