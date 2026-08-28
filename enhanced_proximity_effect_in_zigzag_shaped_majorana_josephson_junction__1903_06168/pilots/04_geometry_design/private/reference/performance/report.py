"""Summarize completed performance evidence without running more physics."""

import hashlib
import json
import os
from pathlib import Path
import statistics
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2] / "participant" / "workspace"))
import physics


def load(name):
    return json.loads((ROOT / name).read_text())


def main():
    summary = load("summary.json")
    direct = load("direct_report.json")
    history = load("direct_history.json")
    request = load("request.json")
    environment = load("environment.json")
    pilot = ROOT.parents[2]
    calibration_path = pilot / "private" / "reference" / "matched_1300_calibration.json"
    calibration = json.loads(calibration_path.read_text())
    model_bytes = (pilot / "participant" / "workspace" / "physics.py").read_bytes()
    assert hashlib.sha256(model_bytes).hexdigest() == environment["forward_model_sha256"]
    assert model_bytes == (pilot / "private" / "reference" / "physics.py").read_bytes()
    assert request == json.loads((pilot / "private" / "challenge_pool" / "matched_1300" / "request.json").read_text())
    assert load("scenarios.json") == json.loads((pilot / "private" / "challenge_pool" / "matched_1300" / "scenarios.json").read_text())
    assert calibration["weak"]["robust_gap_mev"] == summary["weak_reference_robust_gap_mev"]
    assert calibration["strong"]["robust_gap_mev"] == summary["strong_reference_robust_gap_mev"]
    assert summary["complete"]
    assert direct["wall_seconds"] <= direct["wall_budget_seconds"] + 5
    assert direct["numeric_child_cpu_seconds"] <= 2400 + 5
    assert direct["affinity"] == [382, 383]
    rows = []
    forward_times = []
    scenario_times = []
    kernel_calls = []
    peak_rss_kib = []
    successful_durations = []
    for candidate in history:
        measurements = candidate.get("measurements", [])
        for measurement in measurements:
            if measurement.get("status") == "completed":
                assert measurement["dimension"] == 15860
                assert len(measurement["gaps_mev"]) == 51
                assert measurement["affinity"] == [382, 383]
                assert all(pool["num_threads"] == 1 for pool in measurement["threadpools"])
                assert measurement["address_space_limit_bytes"] == 2 * 1024 ** 3
                scenario_times.append(measurement["elapsed_seconds"])
                kernel_calls.extend(measurement["eigensolver_seconds"])
                peak_rss_kib.append(measurement["peak_rss_kib"])
        complete = candidate.get("complete", False)
        feasible = candidate.get("physical_feasibility", False)
        duration = candidate.get("finished_at_seconds", candidate["started_at_seconds"]) - candidate["started_at_seconds"]
        if complete:
            assert len(measurements) == 3
            successful_durations.append(duration)
        if complete and feasible:
            assert all(measurement["class_d_invariant"] == -1 and measurement["gap_mev"] > 1e-5 for measurement in measurements)
        gap = candidate.get("robust_gap_mev")
        normalized = None if not feasible else (gap - summary["weak_reference_robust_gap_mev"]) / (summary["strong_reference_robust_gap_mev"] - summary["weak_reference_robust_gap_mev"])
        forward_seconds = sum(sum(measurement.get("eigensolver_seconds", [])) for measurement in measurements)
        forward_times.append(forward_seconds)
        rows.append({"candidate": candidate["index"], "amplitude_nm": candidate["amplitude_nm"], "width_nm": candidate["perpendicular_width_nm"], "complete": complete, "feasible": feasible, "wall_seconds": duration, "robust_gap_mev": gap, "normalized_core": normalized, "low_energy_call_seconds_summed_across_workers": forward_seconds})
    best = direct["best"]
    assert best is not None
    result = load("best_result.json")
    selected = load(f"candidate_{best['candidate_index']:03d}.json")
    assert result == selected
    masks = physics.geometry_arrays(request, result["geometry"])
    assert physics.feasibility(request, masks)["valid"]
    dense = load("dense_numpy_full_eigh.json")
    in_place = load("dense_scipy_inplace_subset_evr.json")
    assert dense["dimension"] == in_place["dimension"] == 15860
    assert dense["address_space_limit_bytes"] == in_place["address_space_limit_bytes"] == 6 * 1024 ** 3
    assert dense["affinity"] == in_place["affinity"] == [382, 383]
    partials = []
    for path in sorted(ROOT.glob("candidate_*_scenario_*.json")):
        record = json.loads(path.read_text())
        if record.get("status") != "completed":
            partials.append({"file": path.name, "status": record.get("status"), "persisted_momentum_points": len(record.get("gaps_mev", []))})
    normalized = summary["direct_best_normalized_core"]
    reached = summary["direct_reached_or_exceeded_strong"]
    estimates = {
        "unpruned_140_geometry_grid_seconds_at_observed_median_full_evaluation": 140 * statistics.median(successful_durations),
        "dense_153_point_proxy_seconds_at_60s_per_point_and_ideal_two_way_parallelism": 153 * 60 / 2,
        "status": "ESTIMATES ONLY: the exhaustive grid was not run; the dense proxy extrapolates a short single-point watchdog, not a measured full evaluation or proof about every dense implementation.",
    }
    report = {
        "witnessed_dense_default_failure": dense["status"] == "allocation_failure",
        "dense_default_status": dense["status"],
        "dense_default_error": dense.get("error"),
        "dense_inplace_status": in_place["status"],
        "dense_inplace_watchdog_seconds": in_place.get("wall_budget_seconds"),
        "direct_best_normalized_core_single_family": normalized,
        "direct_reached_strong_single_family": reached,
        "candidate_table": rows,
        "partial_scenarios_not_scored": partials,
        "timing": {
            "direct_wall_seconds": direct["wall_seconds"],
            "numeric_children_cpu_seconds": direct["numeric_child_cpu_seconds"],
            "dense_observed_wall_seconds": dense["observed_wall_seconds"] + in_place["observed_wall_seconds"],
            "median_low_energy_call_seconds": statistics.median(kernel_calls),
            "median_full_51_point_scenario_seconds": statistics.median(scenario_times),
            "maximum_worker_peak_rss_mib": max(peak_rss_kib) / 1024,
            "note": "low_energy API timings include Hamiltonian assembly, sparse factorization/eigensolving, and residual checks; they are not isolated LAPACK profiling. Optimization quality is reported separately.",
        },
        "estimated_baselines_not_witnessed": estimates,
        "best_output_verified_against_completed_candidate": True,
        "scope": "matched_1300 only; no aggregate three-family score or universal impossibility claim",
        "setup_failure_excluded": True,
        "no_participant_or_evaluator_changes": True,
        "provenance": {
            "calibration_path": str(calibration_path),
            "calibration_sha256": hashlib.sha256(calibration_path.read_bytes()).hexdigest(),
            "calibration_fingerprint": calibration["fingerprint"],
            "forward_model_sha256": environment["forward_model_sha256"],
            "best_result_sha256": hashlib.sha256((ROOT / "best_result.json").read_bytes()).hexdigest(),
            "inputs_and_model_unchanged_during_run": True,
        },
    }
    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        "# Witnessed performance evidence: pilot04",
        "",
        "## Resource isolation",
        "",
        "Actual numeric affinity: CPUs **382–383**; one BLAS thread; no fresh agents or participant solver launch. All writes are in this performance directory. Dense children had a **6 GiB address-space cap**. Direct search used at most two 2 GiB workers and a 1 GiB-soft-limit parent; its 6 GiB hard ceiling only permits children to establish their own limits.",
        "",
        "## Dense witnesses",
        "",
        f"- Actual full **15,860 × 15,860 complex128** Hamiltonian, {dense['dense_bytes'] / 1024 ** 3:.4f} GiB for one dense matrix.",
        f"- `numpy.linalg.eigh`: **{dense['status']}** in {dense['observed_wall_seconds']:.3f} s total. Actual exception: `{dense.get('error')}`. This is allocation failure during the eigensolver entry, not evidence of a completed numerical kernel.",
        f"- In-place SciPy `evr`, selecting eight central eigenvalues: **{in_place['status']}**, still inside the eigensolver at its {in_place.get('wall_budget_seconds', 60):g} s whole-process watchdog. This does **not** establish a 1200-second timeout. Its resource fields are the last persisted pre-call snapshot, not a measured final peak RSS.",
        "",
        "## Actual direct-forward optimization",
        "",
        "A two-parameter, first-improvement coordinate search starts from the supplied original zigzag. It does not read the archived optimizer or optimized masks. All completed candidates use 51 momenta × three exact robustness points and independent topological checks; using the exact private points favors this baseline. Search updates use only its newly measured robust gaps. The reference scalar is read after search stops.",
        "",
        f"Wall time **{direct['wall_seconds']:.2f} / 1200 s**; numeric-child CPU **{direct['numeric_child_cpu_seconds']:.2f} s**. Best robust gap **{summary['direct_best_robust_gap_mev']:.12f} meV**; weak **{summary['weak_reference_robust_gap_mev']:.12f}**, stored strong **{summary['strong_reference_robust_gap_mev']:.12f} meV**. Unbounded normalized single-family core: **{normalized:.8f}**.",
        "",
        "| Candidate | Amplitude / width (nm) | Full 3×51 | Feasible | Wall s | Robust gap meV | Normalized core |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        gap = "—" if row["robust_gap_mev"] is None else f"{row['robust_gap_mev']:.9f}"
        score = "—" if row["normalized_core"] is None else f"{row['normalized_core']:.6f}"
        lines.append(f"| {row['candidate']} | {row['amplitude_nm']:g} / {row['width_nm']:g} | {row['complete']} | {row['feasible']} | {row['wall_seconds']:.2f} | {gap} | {score} |")
    lines.extend([
        "",
        f"**Finding:** {'The tested generic direct baseline attains or exceeds the stored strong reference; it must not be claimed to fail this target.' if reached else 'The tested generic direct baseline does not attain the stored strong reference within its budget. This is a witnessed outcome for this algorithm, not proof that every generic direct method fails.'}",
        "",
        f"Median full 51-point operating-point time: **{statistics.median(scenario_times):.2f} s**; median `low_energy` call: **{statistics.median(kernel_calls):.3f} s**. These API calls include factorization and residual checks. Maximum observed completed-worker peak RSS: **{max(peak_rss_kib) / 1024:.1f} MiB**. These timings measure forward cost, separately from the attained objective.",
        "",
        "## Explicitly unexecuted estimates",
        "",
        f"- An unpruned 140-geometry parameter grid at the observed median full-evaluation time would cost approximately **{estimates['unpruned_140_geometry_grid_seconds_at_observed_median_full_evaluation'] / 3600:.2f} hours**. This grid was **not executed**; feasibility pruning and shape-dependent costs can change the estimate.",
        "- Extending the 60-second dense single-point watchdog to 153 points with ideal two-way parallelism gives a **4590-second proxy**, not a measured complete evaluation or a universal dense lower bound.",
        "",
        "## Audit and artifacts",
        "",
        "`best_result.json` is identical to the best fully evaluated feasible candidate; partial candidates are excluded. `events.jsonl`, every `candidate_*_scenario_*.json`, `direct_history.json`, `direct_report.json`, and `report.json` preserve timings, exact gaps, topology, affinity, limits, and best-so-far state. `setup_failure/` separately preserves an initial inherited-RLIMIT setup error before any forward calculation; it is excluded from numerical evidence. No running participant files, evaluator, challenge pool, or attempt were changed.",
    ])
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
