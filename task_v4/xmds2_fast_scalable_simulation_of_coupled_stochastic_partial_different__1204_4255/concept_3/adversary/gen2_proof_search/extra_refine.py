import hashlib
import json
import resource
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRUSTED = ROOT / "evaluator/hidden"
sys.path.insert(0, str(TRUSTED))
import field_control as fc


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_frozen(manifest, proof):
    assert all(digest(HERE / name) == expected for name, expected in manifest["sha256"].items())
    assert all(digest(ROOT / name) == expected for name, expected in proof["frozen_sha256"].items())
    assert digest(HERE / "control.json") == proof["control_sha256"]


def compute_record(result):
    runs = []
    for tag in ("risk60", "safe64", "hinge64"):
        provenance = fc.read_json(HERE / (tag + ".provenance.json"))
        completion = fc.read_json(HERE / (tag + ".completion.json"))
        history = fc.read_json(HERE / (tag + ".history.json"), 1024 * 1024)
        start = provenance["started_unix"]
        elapsed = completion["seconds"]
        workers = provenance["parameters"]["workers"]
        runs.append({"tag": tag, "start_unix": start, "end_unix": start + elapsed, "start_pacific": datetime.fromtimestamp(start, ZoneInfo("America/Los_Angeles")).isoformat(), "end_pacific": datetime.fromtimestamp(start + elapsed, ZoneInfo("America/Los_Angeles")).isoformat(), "wall_seconds": elapsed, "workers": workers, "iterations": completion["iterations"], "objective_evaluations": history[-1]["calls"], "cases_per_objective": provenance["case_count"], "parameters": provenance["parameters"]})
    events = sorted([(run["start_unix"], run["workers"]) for run in runs] + [(run["end_unix"], -run["workers"]) for run in runs])
    active = 0
    peak = 0
    for timestamp, change in events:
        active += change
        peak = max(peak, active)
    probes = []
    for path in sorted(HERE.glob("*.log")):
        for line in path.read_text().splitlines():
            if line.startswith("PROBE "):
                record = json.loads(line[6:])
                probes.append({"log": path.name, "source": record["source"], "artifact_sha256": record["artifact_sha256"], "wall_seconds_propagation": record["seconds"], "grid": record["grid"], "dt": record["dt"]})
    return {"role": "privileged_postdeadline_generation_only", "fresh_success": False, "optimization_stopped": True, "live_gen2_attempts_read": False, "runs": runs, "total_iterations": sum(run["iterations"] for run in runs), "total_objective_evaluations": sum(run["objective_evaluations"] for run in runs), "case_objective_evaluations": sum(run["objective_evaluations"] * run["cases_per_objective"] for run in runs), "overlapping_run_wall_seconds_sum": sum(run["wall_seconds"] for run in runs), "optimization_span_wall_seconds": max(run["end_unix"] for run in runs) - min(run["start_unix"] for run in runs), "peak_optimization_workers": peak, "worker_wall_hours_envelope": sum(run["wall_seconds"] * run["workers"] for run in runs) / 3600, "cpu_accounting_note": "Actual historical CPU seconds and peak RSS were not metered. Worker-wall hours are a parallelism-times-wall envelope, not measured CPU hours; parent work, probes and the official grader are separate. No GPU was used.", "surrogate_probes": probes, "surrogate_propagation_wall_seconds_sum": sum(probe["wall_seconds_propagation"] for probe in probes), "surrogate_accounting_note": "Recorded propagation durations exclude reference preparation and overlap with optimization and one another. Gradient checks and authoring overhead were not timed comprehensively.", "official_evaluator_runs": 1, "official_evaluator_wall_seconds": result["runtime_seconds"], "artifact_sha256": digest(HERE / "control.json"), "artifact_canonical_sha256": result["artifact_canonical_sha256"]}


def evolve_dense_boundary(splines, cases, shape, dt, initial):
    steps = int(round(8.0 / dt))
    position_x, position_y, kinetic, volume = fc.geometry(shape)
    parameters = fc.case_arrays(cases)
    controls = np.stack([splines[channel]((np.arange(steps) + 0.5) * dt) for channel in fc.CHANNELS], axis=1)
    kinetic_phase = np.exp(-0.5j * dt * kinetic)
    boundary = (np.abs(position_x) >= 8.0) | (np.abs(position_y) >= 4.8)
    state = initial.copy()
    maxima = np.zeros((3, len(cases)))
    density = np.sum(np.abs(state) ** 2, axis=1)
    dense_boundary = volume * np.sum(density * boundary, axis=(-2, -1))
    peak_time = np.zeros(len(cases))
    dense_norm = np.abs(volume * np.sum(density, axis=(-2, -1)) - 1.0)
    for step_index, values in enumerate(controls):
        trap = fc.potential(parameters, position_x, position_y, values)
        state = fc.split_step(state, kinetic_phase, trap, parameters, parameters["rf_gain"] * values[2], parameters["rf_gain"] * values[3], dt)
        density = np.sum(np.abs(state) ** 2, axis=1)
        mass = volume * np.sum(density * boundary, axis=(-2, -1))
        improved = mass > dense_boundary
        peak_time[improved] = (step_index + 1) * dt
        dense_boundary = np.maximum(dense_boundary, mass)
        dense_norm = np.maximum(dense_norm, np.abs(volume * np.sum(density, axis=(-2, -1)) - 1.0))
        if step_index % 20 == 0 or step_index == steps - 1:
            if not np.all(np.isfinite(state)):
                raise ArithmeticError("Nonfinite extra-refinement state")
            maxima = np.maximum(maxima, np.asarray(fc.diagnostics(state, shape)))
        if (step_index + 1) % 800 == 0:
            print("EXTRA_PROGRESS", step_index + 1, steps, "dense_boundary", dense_boundary.tolist(), flush=True)
    return state, {"norm_error": maxima[0], "boundary_mass": maxima[1], "spectral_tail": maxima[2], "dense_norm_error": dense_norm, "dense_boundary_mass": dense_boundary, "dense_boundary_peak_time": peak_time}


def main():
    started = time.perf_counter()
    cpu_start = resource.getrusage(resource.RUSAGE_SELF)
    manifest = fc.read_json(HERE / "manifest.json", 1024 * 1024)
    proof = fc.read_json(HERE / "proof.json", 1024 * 1024)
    result = fc.read_json(HERE / "evaluation.json", 1024 * 1024)
    verify_frozen(manifest, proof)
    assert result["valid"] and result["passed"]
    protocol = fc.read_json(TRUSTED / "protocol.json")
    cases = fc.read_json(TRUSTED / "cases.json")
    splines, certificate = fc.validate_artifact(fc.read_json(HERE / "control.json"), protocol)
    compute = compute_record(result)
    compute.pop("fresh_success", None)
    compute.update({"role": "privileged_nonfresh_compute_accounting", "is_fresh_submission": False, "source_assets_generation": 1, "fresh_generation_2_outcome": None, "live_generation_2_submissions_read": False})
    dump("compute.json", compute)
    worst_fidelity = int(np.argmin([case["audited_fidelity"] for case in result["cases"]]))
    references_by_shape = {}
    for shape in ((80, 40), (112, 56)):
        path = TRUSTED / "references" / (fc.reference_key(cases, shape) + ".npz")
        if not path.is_file():
            raise RuntimeError("Frozen reference cache missing; refusing any root write")
        references_by_shape[shape] = fc.references(cases, shape, TRUSTED / "references")
    boundary_scans = []
    largest_boundary = None
    expected_boundary = result["audits"]["max_boundary_mass"]
    for shape, dt in (((80, 40), 0.01), ((112, 56), 0.01), ((112, 56), 0.005)):
        scan_started = time.perf_counter()
        state, diagnostics = fc.evolve(splines, cases, shape, dt, references_by_shape[shape][0])
        index = int(np.argmax(diagnostics["boundary_mass"]))
        maximum = float(diagnostics["boundary_mass"][index])
        scan = {"grid": list(shape), "dt": dt, "case_count": len(cases), "maximum_boundary_mass": maximum, "maximum_case_id": cases[index]["id"], "reported_official_global_maximum": expected_boundary, "matches_reported_global_maximum": bool(np.isclose(maximum, expected_boundary, rtol=2e-12, atol=1e-21)), "wall_seconds": time.perf_counter() - scan_started, "cases": [{"id": case["id"], "boundary_mass": float(diagnostics["boundary_mass"][offset])} for offset, case in enumerate(cases)]}
        boundary_scans.append(scan)
        dump("boundary_identification.json", {"scans": boundary_scans})
        print("BOUNDARY_SCAN", json.dumps({key: value for key, value in scan.items() if key != "cases"}), flush=True)
        if scan["matches_reported_global_maximum"]:
            largest_boundary = index
            break
    if largest_boundary is None:
        raise ArithmeticError("Could not reproduce the official global boundary maximum")
    selected = list(dict.fromkeys((worst_fidelity, largest_boundary)))
    selected_cases = [cases[index] for index in selected]
    dump("extra_selected_cases.json", {"selection": [{"case": cases[index], "roles": [label for label, chosen in (("worst_audited_fidelity", worst_fidelity), ("largest_official_boundary_mass", largest_boundary)) if index == chosen]} for index in selected]})
    initial_fine, target_fine, fine_residual = references_by_shape[(112, 56)]
    fine, fine_diagnostics = fc.evolve(splines, selected_cases, (112, 56), 0.005, initial_fine[selected])
    fine_scores = fc.fidelities(fine, target_fine[selected], (112, 56))
    assert np.max(np.abs(fine_scores - np.array([result["cases"][index]["refined_fidelity"] for index in selected]))) < 3e-11
    extra_initial, extra_target, extra_residual = fc.references(selected_cases, (160, 80), HERE / "extra_reference_cache")
    extra, diagnostics = evolve_dense_boundary(splines, selected_cases, (160, 80), 0.0025, extra_initial)
    scores = fc.fidelities(extra, extra_target, (160, 80))
    distances = fc.state_distance(fc.prolong(fine, (160, 80)), extra, (160, 80))
    records = []
    for offset, index in enumerate(selected):
        record = {"case": cases[index], "roles": [label for label, chosen in (("worst_audited_fidelity", worst_fidelity), ("largest_official_boundary_mass", largest_boundary)) if index == chosen], "official_audited_fidelity": result["cases"][index]["audited_fidelity"], "frozen_C_fidelity": float(fine_scores[offset]), "extra_fidelity": float(scores[offset]), "extra_fidelity_margin_over_minimum_target": float(scores[offset] - 0.98), "fidelity_change_from_frozen_C": float(scores[offset] - fine_scores[offset]), "state_distance_from_prolonged_frozen_C": float(distances[offset]), "extra_reference_residual": extra_residual, "frozen_C_reference_residual": fine_residual, "extra_diagnostics": {key: float(values[offset]) for key, values in diagnostics.items()}}
        checks = {"fidelity_above_minimum_target": record["extra_fidelity"] >= 0.98, "fidelity_change_below_allowance_limit": abs(record["fidelity_change_from_frozen_C"]) <= protocol["audit"]["max_allowance"], "state_distance_below_limit": record["state_distance_from_prolonged_frozen_C"] <= protocol["audit"]["max_state_distance"], "reference_residual_below_limit": extra_residual <= protocol["audit"]["max_reference_residual"], "dense_boundary_below_limit": record["extra_diagnostics"]["dense_boundary_mass"] <= protocol["audit"]["max_boundary_mass"], "dense_norm_below_limit": record["extra_diagnostics"]["dense_norm_error"] <= protocol["audit"]["max_norm_error"], "spectral_tail_below_limit": record["extra_diagnostics"]["spectral_tail"] <= protocol["audit"]["max_spectral_tail"]}
        record["checks"] = checks
        record["extra_checks_passed"] = all(checks.values())
        records.append(record)
    verify_frozen(manifest, proof)
    cpu_end = resource.getrusage(resource.RUSAGE_SELF)
    report = {"role": "privileged_postproof_numerical_confirmation", "official_pass_unchanged": True, "artifact_sha256": proof["control_sha256"], "artifact_canonical_sha256": result["artifact_canonical_sha256"], "grid": [160, 80], "dt": 0.0025, "dense_boundary_monitor_interval": 0.0025, "standard_diagnostic_monitor_interval": 0.05, "extra_checks_passed": all(record["extra_checks_passed"] for record in records), "scope_note": "Only the selected two extreme cases receive extra refinement; this is supplementary evidence, not a replacement full-case score or a changed acceptance rule. The boundary mask has grid-dependent quadrature sampling, so raw boundary estimates need not converge monotonically.", "boundary_identification": boundary_scans, "cases": records, "wall_seconds": time.perf_counter() - started, "measured_cpu_user_seconds": cpu_end.ru_utime - cpu_start.ru_utime, "measured_cpu_system_seconds": cpu_end.ru_stime - cpu_start.ru_stime, "peak_rss_kib": cpu_end.ru_maxrss, "original_manifest_files_unchanged": True, "frozen_evaluator_files_unchanged": True}
    dump("extra_refinement.json", report)
    compute["extra_refinement"] = {key: report[key] for key in ("wall_seconds", "measured_cpu_user_seconds", "measured_cpu_system_seconds", "peak_rss_kib")}
    dump("compute.json", compute)
    print("EXTRA_COMPLETE", json.dumps({key: value for key, value in report.items() if key != "boundary_identification"}, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
