import sys

sys.dont_write_bytecode = True

import argparse
from collections import Counter, defaultdict
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
ROOT = PRIVATE.parent


def module(name, relative):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(loaded)
    return loaded


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen():
    manifest = json.loads((ROOT / "evaluator/hidden/frozen_manifest.json").read_text())
    for relative, expected in manifest["files_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("frozen asset hash mismatch: " + relative)
    return sha256(ROOT / "evaluator/hidden/frozen_manifest.json")


def private_output(value):
    path = Path(value).resolve()
    if not path.is_relative_to(PRIVATE.resolve()):
        raise ValueError("all sidecar outputs must remain under concept_2/adversary")
    return path


def geometry():
    graph = json.loads((ROOT / "participant/input/graph.json").read_text())
    projection = np.zeros((39, 20))
    for edge in graph["edges"]:
        for detector in edge["detectors"]:
            projection[edge["id"], detector] = 1 / len(edge["detectors"])
    return graph, projection


def balanced_levels(field, rates, projection):
    raw = projection @ np.asarray(field, dtype=float)
    centered = raw - np.dot(rates, raw) / math.fsum(rates)
    magnitude = np.max(np.abs(centered))
    return None if magnitude < 1e-13 else centered / magnitude


def spatial_fields(random_fields, seed):
    for family, count, region in (
        ("row_corners", 4, lambda detector: detector % 4),
        ("column_corners", 5, lambda detector: detector // 4),
        ("quadrant_corners", 4, lambda detector: 2 * int(detector // 4 >= 2) + int(detector % 4 >= 2)),
    ):
        for index, signs in enumerate(itertools.product((-1, 1), repeat=count)):
            if len(set(signs)) > 1:
                yield family, str(index), [signs[region(detector)] for detector in range(20)]
    for column in range(4):
        for row in range(3):
            for direction in (-1, 1):
                field = [direction * int(column <= detector // 4 <= column + 1 and row <= detector % 4 <= row + 1) for detector in range(20)]
                yield "local_2x2_patch", f"{column}_{row}_{direction}", field
    random = np.random.default_rng(seed)
    for index in range(random_fields):
        field = random.choice([-1.0, 1.0], size=20)
        yield "detector_corners", str(index), field.tolist()
        grid = random.normal(size=(5, 4))
        padded = np.pad(grid, 1, mode="edge")
        smoothed = (padded[1:-1, 1:-1] + padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]) / 5
        yield "smooth_fields", str(index), smoothed.ravel().tolist()


def metrics(rates, syndrome, physical, checker, spec):
    if np.any(rates <= 0) or np.any(1.05 * rates >= 0.5):
        raise ValueError("calibrated probabilities outside physical domain")
    opposite = 1 - physical
    anchors = []
    for scale in spec["anchors"]:
        joint, costs = checker.frontier(rates, syndrome, scale)
        total = float(sum(joint))
        anchors.append({"scale": scale, "joint_probabilities": joint.tolist(), "class_costs": costs.tolist(),
                        "gap": float(costs[opposite] - costs[physical]), "posterior": float(joint[opposite] / total),
                        "log_odds": math.log(float(joint[opposite] / joint[physical])), "mass": total})
    lower, upper = spec["scale_interval"]
    derivative = 39 / lower + math.fsum(rate / (1 - upper * rate) for rate in rates)
    radius = max(second - first for first, second in zip(spec["anchors"], spec["anchors"][1:])) / 2
    allowance = derivative * radius + spec["numerical_guard"]
    minima = {name: min(anchor[name] for anchor in anchors) for name in ("gap", "posterior", "log_odds", "mass")}
    certified = {"gap": minima["gap"] - allowance, "log_odds": minima["log_odds"] - allowance,
                 "mass": minima["mass"] * math.exp(-allowance)}
    certified["posterior"] = 1 / (1 + math.exp(-certified["log_odds"]))
    targets = {"gap": spec["targets"]["gap"], "posterior": spec["targets"]["opposite_posterior"], "mass": spec["targets"]["syndrome_probability"]}
    actual_failures = ["lost_" + name for name in targets if minima[name] < targets[name]]
    certificate_failures = ["lost_" + name for name in targets if certified[name] < targets[name]]
    target_log_odds = math.log(targets["posterior"] / (1 - targets["posterior"]))
    actual_score = min(minima["gap"] / targets["gap"], minima["log_odds"] / target_log_odds, minima["mass"] / targets["mass"])
    certified_score = min(certified["gap"] / targets["gap"], certified["log_odds"] / target_log_odds, certified["mass"] / targets["mass"])
    return {"physical_class": physical, "anchors": anchors, "anchor_minima": minima, "certified": certified,
            "allowance": allowance, "actual_failures": actual_failures, "certificate_failures": certificate_failures,
            "certificate_only_failure": bool(certificate_failures) and not actual_failures,
            "physical_class_changed_at_anchor": minima["gap"] < 0,
            "inversion_destroyed_at_anchor": minima["posterior"] <= 0.5,
            "actual_anchor_score": actual_score, "certified_score": certified_score}


def mirror(artifact, graph, columns, rows):
    detector_map = {detector: 4 * (4 - detector // 4 if columns else detector // 4) + (3 - detector % 4 if rows else detector % 4) for detector in range(20)}
    lookup = {(tuple(edge["detectors"]), edge["boundary"]): edge["id"] for edge in graph["edges"]}
    transformed = {"version": 1, "probabilities": [0.0] * 39, "syndrome": sorted(detector_map[detector] for detector in artifact["syndrome"])}
    for edge in graph["edges"]:
        boundary = edge["boundary"]
        if columns and boundary is not None:
            boundary = "right" if boundary == "left" else "left"
        mapped = tuple(sorted(detector_map[detector] for detector in edge["detectors"]))
        transformed["probabilities"][lookup[mapped, boundary]] = artifact["probabilities"][edge["id"]]
    return transformed, len(artifact["syndrome"]) % 2 if columns else 0


def symmetry_checks(artifact, graph, checker):
    checks = []
    for control, syndrome in (("submitted", artifact["syndrome"]), ("odd_syndrome_control", [0, 5, 10])):
        data = {**artifact, "syndrome": syndrome}
        for columns, rows in ((False, True), (True, False), (True, True)):
            transformed, logical_shift = mirror(data, graph, columns, rows)
            checker.validate(transformed)
            mass_error, cost_error = 0.0, 0.0
            for scale in (0.95, 1.0, 1.05):
                original = checker.frontier(data["probabilities"], syndrome, scale)
                changed = checker.frontier(transformed["probabilities"], transformed["syndrome"], scale)
                order = [logical_shift, 1 ^ logical_shift]
                np.testing.assert_allclose(original[0], changed[0][order], rtol=3e-12, atol=0)
                np.testing.assert_allclose(original[1], changed[1][order], rtol=3e-12, atol=1e-12)
                mass_error = max(mass_error, float(np.max(np.abs(original[0] / changed[0][order] - 1))))
                cost_error = max(cost_error, float(np.max(np.abs(original[1] - changed[1][order]))))
            checks.append({"control": control, "columns_reflected": columns, "rows_reflected": rows,
                           "logical_xor": logical_shift, "mass_relative_error": mass_error,
                           "cost_absolute_error": cost_error, "passed": True})
    return checks


def independent_checks(artifact, cases, checker, oracle, seed):
    target = sum(1 << detector for detector in artifact["syndrome"])
    masks = np.array(oracle.edge_masks(), dtype=np.int64)
    rates = np.array(artifact["probabilities"])
    checks = []
    selected = []
    for metric in ("gap", "posterior", "mass"):
        case = min(cases, key=lambda item: item["metrics"]["anchor_minima"][metric])
        anchor = min(case["metrics"]["anchors"], key=lambda item: item[metric])
        selected.append((metric, case, anchor["scale"], np.arange(39)))
    smallest_amplitude = min(case["amplitude"] for case in cases if case["amplitude"] > 0)
    small_cases = [case for case in cases if case["amplitude"] == smallest_amplitude]
    small_case = min(small_cases, key=lambda item: item["metrics"]["anchor_minima"]["gap"])
    small_anchor = min(small_case["metrics"]["anchors"], key=lambda item: item["gap"])
    selected.append(("smallest_amplitude_gap", small_case, small_anchor["scale"], np.arange(39)))
    nominal = cases[0]
    selected.append(("edge_order_reverse", nominal, 1.0, np.arange(38, -1, -1)))
    selected.append(("edge_order_seeded_permutation", nominal, 0.95, np.random.default_rng(seed + 1).permutation(39)))
    for label, case, scale, order in selected:
        calibrated = rates * np.array(case["multipliers"]) * scale
        full = oracle.full_state(calibrated[order], masks[order], 20, target=target)
        fast = checker.frontier(rates * np.array(case["multipliers"]), artifact["syndrome"], scale)
        np.testing.assert_allclose(full[0], fast[0], rtol=3e-12, atol=0)
        np.testing.assert_allclose(full[1], fast[1], rtol=3e-12, atol=1e-12)
        physical = case["metrics"]["physical_class"]
        checks.append({"purpose": label, "case_id": case["case_id"], "scale": scale,
                       "joint_probabilities": full[0].tolist(), "class_costs": full[1].tolist(),
                       "gap": float(full[1][1 - physical] - full[1][physical]),
                       "posterior": float(full[0][1 - physical] / sum(full[0])), "mass": float(sum(full[0])),
                       "mass_relative_error": float(np.max(np.abs(full[0] / fast[0] - 1))),
                       "cost_absolute_error": float(np.max(np.abs(full[1] - fast[1]))), "passed": True})
    return checks


def aggregate(cases):
    groups = defaultdict(list)
    for case in cases:
        if case["family"] != "nominal":
            groups[f"{case['family']}@{case['amplitude']:.3f}"].append(case)
    result = {}
    for label, group in groups.items():
        result[label] = {"cases": len(group),
                         "actual_failure_clusters": dict(Counter("+".join(case["metrics"]["actual_failures"]) or "none" for case in group)),
                         "certificate_failure_clusters": dict(Counter("+".join(case["metrics"]["certificate_failures"]) or "none" for case in group)),
                         "certificate_only_failures": sum(case["metrics"]["certificate_only_failure"] for case in group),
                         "anchor_minima": {metric: min(case["metrics"]["anchor_minima"][metric] for case in group) for metric in ("gap", "posterior", "mass")},
                         "certificate_minima": {metric: min(case["metrics"]["certified"][metric] for case in group) for metric in ("gap", "posterior", "mass")}}
    return result


def run(artifact, amplitudes, random_fields, seed, independent=True):
    started = time.monotonic()
    frozen_hash = verify_frozen()
    checker = module("stress_public_checker", "participant/workspace/check.py")
    oracle = module("stress_independent_oracle", "evaluator/hidden/oracle.py")
    checker.validate(artifact)
    spec = json.loads((ROOT / "participant/input/spec.json").read_text())
    graph, projection = geometry()
    rates = np.array(artifact["probabilities"])
    costs = checker.frontier(rates, artifact["syndrome"], 1.0)[1]
    physical = int(costs[1] < costs[0])
    nominal = metrics(rates, artifact["syndrome"], physical, checker, spec)
    cases = [{"case_id": "nominal", "family": "nominal", "amplitude": 0.0, "multipliers": [1.0] * 39, "metrics": nominal}]
    fields = list(spatial_fields(random_fields, seed))
    for amplitude in amplitudes:
        seen = set()
        for family, name, field in fields:
            levels = balanced_levels(field, rates, projection)
            if levels is None:
                continue
            fingerprint = (family, tuple(np.round(levels, 12)))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            multipliers = 1 + amplitude * levels
            drift = float(np.dot(rates, multipliers - 1))
            assert abs(drift) < 2e-14 and np.max(np.abs(multipliers - 1)) <= amplitude + 1e-14
            cases.append({"case_id": f"{family}/{name}@{amplitude:.3f}", "family": family,
                          "amplitude": amplitude, "detector_field": field, "multipliers": multipliers.tolist(),
                          "expected_error_count_drift": drift,
                          "metrics": metrics(rates * multipliers, artifact["syndrome"], physical, checker, spec)})
    symmetries = symmetry_checks(artifact, graph, checker)
    independent_results = independent_checks(artifact, cases, checker, oracle, seed) if independent else []
    worst = {metric: min(cases[1:], key=lambda case: case["metrics"]["anchor_minima"][metric])["case_id"] for metric in ("gap", "posterior", "mass")}
    violating = [case for case in cases[1:] if case["metrics"]["actual_failures"]]
    strongest = min(violating, key=lambda case: case["metrics"]["actual_anchor_score"]) if violating else None
    assert verify_frozen() == frozen_hash
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "mode": "private_unfrozen_calibration_stress",
            "artifact_sha256": hashlib.sha256(json.dumps(artifact, sort_keys=True).encode()).hexdigest(),
            "frozen_manifest_sha256_unchanged": frozen_hash, "writes_confined_to": "concept_2/adversary/",
            "policy": {"multipliers": "1 + amplitude * centered_normalized_endpoint_average_detector_field",
                       "centering": "weighted by nominal edge probabilities; sum(p*multiplier) == sum(p)",
                       "base_design_bounds_reapplied_to_calibrated_rates": False,
                       "logical_class_fixed_at_unperturbed_alpha_1": True,
                       "global_scale_interval": spec["scale_interval"], "per_profile_global_interval_certified": True,
                       "entire_local_uncertainty_box_certified": False,
                       "existing_targets_diagnostic_only": spec["targets"], "no_generation_or_threshold_change": True},
            "seed": seed, "amplitudes": amplitudes, "random_fields_per_family": random_fields,
            "total_cases_including_nominal": len(cases), "groups": aggregate(cases),
            "worst_case_by_actual_metric": worst, "strongest_actual_failure": strongest["case_id"] if strongest else None,
            "actual_failure_mechanisms": {name: sum(name in case["metrics"]["actual_failures"] for case in cases[1:]) for name in ("lost_gap", "lost_posterior", "lost_mass")},
            "all_profiles_certify_inversion": all(case["metrics"]["certified"]["gap"] > 0 and case["metrics"]["certified"]["posterior"] > 0.5 for case in cases),
            "symmetry_checks": symmetries, "independent_checks": independent_results,
            "independent_checks_performed": independent, "cases": cases, "elapsed_seconds": time.monotonic() - started}


def write_summary(report, path):
    lookup = {case["case_id"]: case for case in report["cases"]}
    lines = ["# Private local-calibration stress report", "", "NOT a new task generation or a frozen ratchet. Never expose this sidecar to running agents.", "",
             "The input is validated once as a nominal design. Calibrated rates are not clipped back to design bounds: that would erase calibration error.",
             "Every nontrivial profile preserves the total expected error count exactly up to floating-point roundoff. Thus these failures are not disguised global noise increases.",
             "Detector IDs and logical cut stay fixed during calibration. Graph automorphisms are separate invariance controls, not physical adversaries.", "",
             "## Lowest exact metrics", ""]
    targets = report["policy"]["existing_targets_diagnostic_only"]
    target_names = {"gap": "gap", "posterior": "opposite_posterior", "mass": "syndrome_probability"}
    for metric, case_id in report["worst_case_by_actual_metric"].items():
        case = lookup[case_id]
        anchor = min(case["metrics"]["anchors"], key=lambda record: record[metric])
        outcome = "TARGET VIOLATED" if anchor[metric] < targets[target_names[metric]] else "target still met at all anchors"
        lines.append(f"- {metric}: `{case_id}`, alpha={anchor['scale']:.3f}; exact gap={anchor['gap']:.12g}, opposite posterior={anchor['posterior']:.12g}, mass={anchor['mass']:.12g}. {outcome}.")
    lines += ["", "## Family failure clusters", "", "Counts are suite entries, sometimes repeated across families, not estimated calibration-failure probabilities.", "", "| Family @ amplitude | Cases | Actual anchor failures | Certificate-only failures |", "|---|---:|---|---:|"]
    for family, summary in report["groups"].items():
        lines.append(f"| {family} | {summary['cases']} | {json.dumps(summary['actual_failure_clusters'], sort_keys=True)} | {summary['certificate_only_failures']} |")
    lines += ["", "## Interpretation and continuation", "",
              "An exact anchor below a target is a genuine physical failure of that proposed extension. A failed lower-bound certificate alone does not establish a physical failure.",
              "The original frozen task remains satisfied or not according to its unchanged nominal checker; local calibration is additional, currently unscored stress.",
              f"Actual anchor-failure counts: {json.dumps(report['actual_failure_mechanisms'], sort_keys=True)}. All profiles still certify the basic entropy inversion throughout the global interval: {report['all_profiles_certify_inversion']}.",
              "All reported interval bounds cover the global alpha interval for each listed local profile. Corner profiles do NOT certify the continuum of local fields; no extremum-at-corners theorem is assumed.", ""]
    for amplitude in report["amplitudes"]:
        subset = [case for case in report["cases"] if case["amplitude"] == amplitude]
        bounds = {metric: min(case["metrics"]["certified"][metric] for case in subset) for metric in ("gap", "posterior", "mass")}
        lines.append(f"At local amplitude {amplitude:.3f}, known-input certified lower bounds across the finite suite are gap={bounds['gap']:.12g}, posterior={bounds['posterior']:.12g}, mass={bounds['mass']:.12g}.")
    lines += ["", "A plausible continuation retains every original nominal target and adds explicitly declared local-calibration profiles with separate guard margins. The bounds above supply a known feasible envelope for this input, not thresholds to freeze automatically. Test the actual champion first; no new generation or secret condition is created here.",
              "There is no new optimized design witness in this sidecar. Whether the original strict targets can survive a whole independent local-calibration box remains unproved.", "",
              "## Integrity controls", "",
              f"- {len(report['symmetry_checks'])} reflection controls pass, including odd-syndrome logical-class XOR under left/right exchange.",
              f"- {len(report['independent_checks'])} generic 2**21-state checks were run, including reordered edge processing: {report['independent_checks_performed']}.",
              "- Frozen participant/evaluator manifest hashes match before and after; no status writes or fresh runner calls occur.",
              "- Exact means exhaustive positive DP and min-plus inference in binary64, not sampling or a rational-arithmetic claim."]
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("witness")
    parser.add_argument("--output", default=str(PRIVATE / "stress_report.json"))
    parser.add_argument("--summary", default=str(PRIVATE / "STRESS_REPORT.md"))
    parser.add_argument("--amplitudes", type=float, nargs="+", default=[0.02, 0.05])
    parser.add_argument("--random-fields", type=int, default=128)
    parser.add_argument("--seed", type=int, default=230315933)
    parser.add_argument("--skip-independent", action="store_true")
    arguments = parser.parse_args()
    if any(not math.isfinite(amplitude) or amplitude <= 0 or amplitude > 0.05 for amplitude in arguments.amplitudes):
        parser.error("amplitudes must be finite and in (0,0.05]")
    if not 0 <= arguments.random_fields <= 4096:
        parser.error("random-fields must be in [0,4096]")
    output = private_output(arguments.output)
    summary = private_output(arguments.summary)
    oracle = module("stress_artifact_reader", "evaluator/hidden/oracle.py")
    artifact = oracle.read_artifact(arguments.witness)
    report = run(artifact, sorted(set(arguments.amplitudes)), arguments.random_fields, arguments.seed, not arguments.skip_independent)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    write_summary(report, summary)
    print(json.dumps({"report": str(output), "summary": str(summary), "cases": report["total_cases_including_nominal"], "worst_cases": report["worst_case_by_actual_metric"], "independent_checks": len(report["independent_checks"]), "frozen_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
