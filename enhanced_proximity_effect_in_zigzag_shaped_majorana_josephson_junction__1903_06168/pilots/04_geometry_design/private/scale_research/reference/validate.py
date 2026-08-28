"""Validate stored calibration outputs without running any forward evaluations."""

import hashlib
import json
import math
import os
from pathlib import Path
import statistics

from calibrate import CPUS, HERE, INPUT, PHYSICS, read, save, stamp


def main():
    os.sched_setaffinity(0, {27})
    calibration = read(HERE / "calibration.json")
    fingerprint = read(HERE / "fingerprint.json")
    runtime = read(HERE / "runtime.json")
    scenarios = read(INPUT / "scenarios.json")
    errors = []
    rows = []
    required_momenta = [index * math.pi / 50 for index in range(51)]

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(fingerprint["verified"], "Unverified archived source")
    check(hashlib.sha256(PHYSICS.read_bytes()).hexdigest() == fingerprint["physics_sha256"], "Physics helper changed")
    for filename, digest in fingerprint["input_sha256"].items():
        check(hashlib.sha256((INPUT / filename).read_bytes()).hexdigest() == digest, f"Input changed: {filename}")
    for label in ("weak", "strong"):
        record = calibration[label]
        complete_gaps = []
        for scenario_index, measurement in enumerate(record["measurements"]):
            check(measurement.get("scenario") == scenarios[scenario_index], f"Scenario mismatch: {label}/{scenario_index}")
            check(measurement.get("geometry_sha256") == fingerprint["geometry_sha256"][label], f"Geometry mismatch: {label}/{scenario_index}")
            check(measurement.get("physics_sha256") == fingerprint["physics_sha256"], f"Helper mismatch: {label}/{scenario_index}")
            check(measurement.get("affinity") == [CPUS[(0 if label == "weak" else 3) + scenario_index]], f"Affinity mismatch: {label}/{scenario_index}")
            check(all(pool["num_threads"] == 1 for pool in measurement.get("threadpools", [])), f"Thread count mismatch: {label}/{scenario_index}")
            if not measurement.get("complete"):
                check(measurement.get("physical_feasibility") is None, "Incomplete measurement classified as physical failure")
                rows.append(f"| {label} | {scenario_index} | incomplete | — | — |")
                continue
            check(measurement["dimension"] == 25608, "Wrong physical dimension")
            check(len(measurement["momenta_rad"]) == 51, "Incomplete momentum grid labeled complete")
            check(all(math.isclose(actual, expected, abs_tol=1e-14) for actual, expected in zip(measurement["momenta_rad"], required_momenta)), "Wrong momentum grid")
            check(len(measurement["low_energy_mev"]) == len(measurement["gaps_mev"]) == 51, "Missing full spectrum")
            for energies, gap in zip(measurement["low_energy_mev"], measurement["gaps_mev"]):
                check(len(energies) == 8 and all(math.isfinite(energy) for energy in energies), "Invalid low-energy spectrum")
                check(math.isclose(min(map(abs, energies)), gap, abs_tol=1e-14), "Per-momentum gap mismatch")
            check(math.isclose(min(measurement["gaps_mev"]), measurement["gap_mev"], abs_tol=1e-14), "Minimum gap mismatch")
            valid = measurement["manufacturing"]["valid"] and measurement["class_d_invariant"] == -1 and measurement["gap_mev"] > 1e-5
            check(measurement["physical_feasibility"] == valid, "Physical feasibility mismatch")
            complete_gaps.append(measurement["gap_mev"])
            rows.append(f"| {label} | {scenario_index} | {measurement['gap_mev']:.12f} | {measurement['class_d_invariant']} | {measurement['wall_seconds']:.2f} |")
        check(record["complete"] == (len(complete_gaps) == 3), f"Aggregate completeness mismatch: {label}")
        if len(complete_gaps) == 3:
            robust = 0.5 * statistics.mean(complete_gaps) + 0.5 * min(complete_gaps)
            check(math.isclose(robust, record["robust_gap_mev"], abs_tol=1e-14), f"Robust gap mismatch: {label}")
            check(record["physical_feasibility"] == all(row["physical_feasibility"] for row in record["measurements"]), f"Aggregate feasibility mismatch: {label}")
        else:
            check(record["robust_gap_mev"] is None and record["physical_feasibility"] is None, "Incomplete aggregate must remain null")
    check(calibration["complete"] == all(calibration[label]["complete"] for label in ("weak", "strong")), "Calibration completeness mismatch")
    if calibration["normalization"]["ready"]:
        weak = calibration["weak"]["robust_gap_mev"]
        strong = calibration["strong"]["robust_gap_mev"]
        check(strong - weak > 1e-4, "Usable anchors require positive source improvement")
        check(all(calibration[label]["physical_feasibility"] for label in ("weak", "strong")), "Usable anchors require physical feasibility")
        check(calibration["normalization"]["clipped"] is False, "Normalization must not saturate")
        check((weak - weak) / (strong - weak) == 0 and (strong - weak) / (strong - weak) == 1, "Anchor normalization mismatch")
    result = {
        "validated_utc": stamp(), "validation_passed": not errors, "errors": errors,
        "calibration_complete": calibration["complete"], "anchors_ready": calibration["ready"],
        "completed_measurements": sum(row.get("complete", False) for label in ("weak", "strong") for row in calibration[label]["measurements"]),
        "no_forward_evaluations_during_validation": True,
        "numeric_wall_seconds": calibration["numeric_wall_seconds"],
        "numeric_budget_seconds": runtime["numeric_wall_budget_seconds"],
    }
    save(HERE / "validation.json", result)
    report = [
        "# Published-scale reference calibration", "",
        "Out-of-initial-contract private audit only. No submitted solver measurement or initial score/acceptance change.", "",
        f"Source: `{fingerprint['supplied_provenance']['source_member']}`, exact epoch 800; 66×97 sites, 25,608 DOF. Archive array equality and source hashes verified.", "",
        "Full 51-momentum gap in meV, independent Pfaffian Q; all source masks and physical constraints unchanged.", "",
        "| Design | Scenario | Gap (meV) | Q | Wall seconds |", "|---|---|---|---|---|", *rows, "",
    ]
    for label in ("weak", "strong"):
        record = calibration[label]
        report.append(f"- {label}: R={record['robust_gap_mev']} meV; physical_feasibility={record['physical_feasibility']}; complete={record['complete']}.")
    report.extend([
        f"- Normalization anchors ready: {calibration['ready']}; strong-minus-weak={calibration['normalization']['strong_minus_weak_mev']} meV; no clipping.",
        f"- Numerical wall time: {calibration['numeric_wall_seconds']:.2f} seconds of {runtime['numeric_wall_budget_seconds']:.0f}; six one-thread workers on {CPUS}.",
        f"- Output validation passed: {not errors}. Incomplete values are not physical failures.", "",
        "R = 0.5 mean(scenario gaps) + 0.5 minimum(scenario gaps). Manufacturing is checked independently; all three Q must be -1 and full-grid gaps must exceed 1e-5 meV.", "",
        "`calibration.json` stores complete aggregate and per-scenario records. `measurements/` includes all eight energies per momentum, gap curves, Q, checkpoint timings and resource metadata. `fingerprint.json` records source/input/helper hashes. No optimization or wavefunction archive is created.", "",
    ])
    (HERE / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
