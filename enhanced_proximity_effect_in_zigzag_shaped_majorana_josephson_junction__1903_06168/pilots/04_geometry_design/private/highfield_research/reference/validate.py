"""Validate fixed-reference outputs without evaluating submitted geometries."""

import hashlib
import json
import math
import os
import statistics

from calibrate import CONTROLLER_CPU, CPUS, HERE, INPUT, PHYSICS, SCOPE, read, save, stamp


def main():
    os.sched_setaffinity(0, {CONTROLLER_CPU})
    calibration = read(HERE / "calibration.json")
    fingerprint = read(HERE / "fingerprint.json")
    runtime = read(HERE / "runtime.json")
    request = read(INPUT / "request.json")
    scenarios = read(INPUT / "scenarios.json")
    errors = []
    table = []
    completed_count = 0
    required_momenta = [index * math.pi / 50 for index in range(51)]
    dimension = 4 * request["grid"]["ny"] * request["grid"]["nx"]

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(fingerprint["verified"], "Source/baseline identities not verified")
    check(hashlib.sha256(PHYSICS.read_bytes()).hexdigest() == fingerprint["physics_sha256"], "Physics helper changed")
    for filename, digest in fingerprint["input_sha256"].items():
        check(hashlib.sha256((INPUT / filename).read_bytes()).hexdigest() == digest, f"Input changed: {filename}")
    check(dimension == fingerprint["dimension"] == calibration["dimension"] == 15860, "Wrong physical dimension")
    for label in ("weak", "strong"):
        record = calibration[label]
        complete_gaps = []
        for scenario_index, measurement in enumerate(record["measurements"]):
            if not measurement.get("complete"):
                check(measurement.get("physical_feasibility") is None, "Incomplete measurement classified as physical failure")
                table.append(f"| {label} | {scenario_index} | incomplete | — | — |")
                continue
            completed_count += 1
            check(measurement["scenario"] == scenarios[scenario_index], f"Scenario mismatch: {label}/{scenario_index}")
            check(measurement["geometry_sha256"] == fingerprint["geometry_sha256"][label], f"Geometry mismatch: {label}/{scenario_index}")
            check(measurement["physics_sha256"] == fingerprint["physics_sha256"], f"Helper mismatch: {label}/{scenario_index}")
            check(measurement["affinity"] == [CPUS[(0 if label == "weak" else 3) + scenario_index]], f"Affinity mismatch: {label}/{scenario_index}")
            check(bool(measurement["threadpools"]) and all(pool["num_threads"] == 1 for pool in measurement["threadpools"]), "BLAS thread count mismatch")
            check(measurement["dimension"] == dimension, "Worker dimension mismatch")
            check(len(measurement["momenta_rad"]) == len(measurement["low_energy_mev"]) == len(measurement["gaps_mev"]) == 51, "Incomplete grid labeled complete")
            check(all(math.isclose(actual, expected, abs_tol=1e-14) for actual, expected in zip(measurement["momenta_rad"], required_momenta)), "Wrong momentum grid")
            for energies, gap in zip(measurement["low_energy_mev"], measurement["gaps_mev"]):
                check(len(energies) == 8 and all(math.isfinite(energy) for energy in energies), "Invalid low-energy spectrum")
                check(math.isclose(min(map(abs, energies)), gap, abs_tol=1e-14), "Per-momentum gap mismatch")
            check(math.isclose(min(measurement["gaps_mev"]), measurement["gap_mev"], abs_tol=1e-14), "Minimum gap mismatch")
            valid = measurement["manufacturing"]["valid"] and measurement["class_d_invariant"] == -1 and measurement["gap_mev"] > 1e-5
            check(measurement["physical_feasibility"] == valid, "Physical feasibility mismatch")
            complete_gaps.append(measurement["gap_mev"])
            table.append(f"| {label} | {scenario_index} | {measurement['gap_mev']:.12f} | {measurement['class_d_invariant']} | {measurement['wall_seconds']:.2f} |")
        check(record["complete"] == (len(complete_gaps) == 3), f"Aggregate completeness mismatch: {label}")
        if len(complete_gaps) == 3:
            robust = 0.5 * statistics.mean(complete_gaps) + 0.5 * min(complete_gaps)
            check(math.isclose(robust, record["robust_gap_mev"], abs_tol=1e-14), f"Robust gap mismatch: {label}")
            check(record["physical_feasibility"] == all(row["physical_feasibility"] for row in record["measurements"]), f"Aggregate feasibility mismatch: {label}")
        else:
            check(record["robust_gap_mev"] is None and record["physical_feasibility"] is None, "Incomplete aggregate must remain null")
    check(calibration["complete"] == (completed_count == 6), "Calibration completeness mismatch")
    expected_ready = False
    if calibration["complete"]:
        difference = calibration["strong"]["robust_gap_mev"] - calibration["weak"]["robust_gap_mev"]
        check(math.isclose(difference, calibration["normalization"]["strong_minus_weak_mev"], abs_tol=1e-14), "Normalization separation mismatch")
        expected_ready = all(calibration[label]["physical_feasibility"] for label in ("weak", "strong")) and difference > 1e-4 and calibration["source_and_inputs_unchanged"]
    check(calibration["ready"] == calibration["normalization"]["ready"] == expected_ready, "Incorrect anchor readiness")
    check(calibration["normalization"]["clipped"] is False, "Normalization must not saturate")
    if expected_ready:
        check(calibration["normalization"]["weak_anchor"] == 0 and calibration["normalization"]["strong_anchor"] == 1, "Wrong normalization anchors")
    result = {
        "validated_utc": stamp(), "validation_passed": not errors, "errors": errors,
        "calibration_complete": calibration["complete"], "anchors_ready": calibration["ready"],
        "completed_measurements": completed_count, "no_forward_evaluations_during_validation": True,
        "numeric_wall_seconds": calibration["numeric_wall_seconds"], "numeric_budget_seconds": runtime["numeric_wall_budget_seconds"],
    }
    save(HERE / "validation.json", result)
    report = [
        "# Narrowed-high-field fixed-reference calibration", "", SCOPE + ".", "",
        "Strong is exact archived homogeneous_filtered.p epoch 800; weak is the unchanged original zigzag. Source-member hashes and array equality verified. No geometry edits.", "",
        f"Physical grid: {request['grid']['ny']}×{request['grid']['nx']} sites; {dimension:,} DOF; spacing {request['grid']['spacing_nm']} nm.", "",
        "Scenario order (mu_normal, EZ), meV: " + "; ".join(f"{index}: ({scenario['mu_normal_mev']}, {scenario['zeeman_mev']})" for index, scenario in enumerate(scenarios)) + ".", "",
        "| Design | Scenario | Full-51 gap (meV) | Independent Q | Wall seconds |", "|---|---|---|---|---|", *table, "",
    ]
    for label in ("weak", "strong"):
        record = calibration[label]
        report.append(f"- {label}: R={record['robust_gap_mev']} meV; physical_feasibility={record['physical_feasibility']}; complete={record['complete']}.")
    report.extend([
        f"- Unbounded anchors ready: {calibration['ready']}; strong-minus-weak={calibration['normalization']['strong_minus_weak_mev']} meV.",
        f"- Numerical wall time: {calibration['numeric_wall_seconds']:.2f} seconds of {runtime['numeric_wall_budget_seconds']:.0f}; six one-thread workers on {CPUS}.",
        f"- Stored-output validation passed: {not errors}; incomplete values are not failures.", "",
        "R = 0.5 mean(scenario gaps) + 0.5 minimum(scenario gaps). Feasibility includes unchanged manufacturing, all three independent Q=-1, and each full-51 gap > 1e-5 meV.", "",
        "This is a fixed-reference calibration, not a comparison with the adapted submitted solver. The broad-region output's high-field tradeoff is insufficient by itself to establish hardness. Main owns the adaptation run and subsequent interpretation; no initial scoring or public files are changed.", "",
        "Full arrays and metadata: calibration.json and measurements/. Source/input/helper hashes: fingerprint.json. No optimizer or submitted geometry is executed here.", "",
    ])
    (HERE / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
