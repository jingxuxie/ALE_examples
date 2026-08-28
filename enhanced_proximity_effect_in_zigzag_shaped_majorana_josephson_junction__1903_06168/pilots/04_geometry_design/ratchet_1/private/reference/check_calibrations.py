"""Validate all fixed cases and score stored anchors without new physics runs."""

import json
import math
import os

from run_calibrations import ASSIGNMENTS, HERE, PRIVATE, RUNS, evaluator_module, read, save, sha256, stamp


def main():
    os.sched_setaffinity(0, {69})
    evaluator = evaluator_module()
    manifest = read(HERE / "calibration_run_manifest.json")
    execution = read(HERE / "calibration_execution.json")
    runtime = read(HERE / "calibration_runtime.json")
    errors = []
    case_records = []
    score_records = {"weak": [], "strong": []}
    protected_unchanged = all(sha256(PRIVATE / name) == digest for name, digest in manifest["protected_sha256"].items())
    if not protected_unchanged:
        errors.append("One or more protected case/source/evaluator inputs changed")
    actual_cases = {path.name for path in (PRIVATE / "challenge_pool").iterdir() if path.is_dir()}
    if actual_cases != set(ASSIGNMENTS):
        errors.append("The preregistered case set changed")
    requested_momenta = [index * math.pi / 50 for index in range(51)]
    for case in ASSIGNMENTS:
        case_errors = []
        request = read(PRIVATE / "challenge_pool" / case / "request.json")
        scenarios = read(PRIVATE / "challenge_pool" / case / "scenarios.json")
        strong = evaluator.load_result(request, HERE / f"{case}.json")
        weak = evaluator.geometry_arrays(request, request["baseline_geometry"])
        expected_fingerprint = evaluator.fingerprint(request, scenarios, strong)
        calibration_path = HERE / f"{case}_calibration.json"
        calibration = read(calibration_path) if calibration_path.exists() else None
        output_path = RUNS / f"{case}.json"
        output = read(output_path) if output_path.exists() else None
        diagnostic = {
            "request_id": case, "fingerprint": expected_fingerprint,
            "momentum_points": 51, "scoring_rule": evaluator.SCORING_RULE,
            "ready": False, "reconstructed_from_unchanged_evaluator_checkpoints": calibration is None,
        }
        record = {
            "request_id": case, "scenarios": scenarios,
            "execution": execution["cases"].get(case), "complete": False,
            "reference_gate_pass": False, "incomplete_is_failure": False,
            "strong_minus_weak_mev": None, "anchor_scores": None,
        }
        for label, masks in (("weak", weak), ("strong", strong)):
            geometry_status = evaluator.feasibility(request, masks)
            checkpoint_path = HERE / f"{case}_{label}_measurements.json"
            checkpoint = read(checkpoint_path) if checkpoint_path.exists() else None
            rows = checkpoint.get("measurements", []) if checkpoint else []
            if checkpoint and (checkpoint.get("fingerprint") != expected_fingerprint or checkpoint.get("momentum_points") != 51):
                case_errors.append(f"{label}: stale or wrong-resolution checkpoint")
            complete = len(rows) == 3 and all(len(row.get("momenta_rad", [])) == len(row.get("gaps_mev", [])) == 51 for row in rows)
            anchor = {
                "complete": complete, "geometry": geometry_status,
                "physical_feasibility": None, "robust_gap_mev": None,
                "mean_gap_mev": None, "worst_gap_mev": None,
                "scenario_gaps_mev": None, "class_d_invariants": None,
                "scenario_seconds": None,
            }
            if complete:
                for scenario_index, row in enumerate(rows):
                    if row["scenario"] != scenarios[scenario_index] or row["dimension"] != 25608:
                        case_errors.append(f"{label}/{scenario_index}: wrong scenario or dimension")
                    if row["class_d_invariant"] not in (-1, 1):
                        case_errors.append(f"{label}/{scenario_index}: unresolved topology")
                    if not all(math.isfinite(gap) and gap >= 0 for gap in row["gaps_mev"]):
                        case_errors.append(f"{label}/{scenario_index}: invalid spectral gaps")
                    if not all(math.isclose(actual, expected, abs_tol=1e-14) for actual, expected in zip(row["momenta_rad"], requested_momenta)):
                        case_errors.append(f"{label}/{scenario_index}: incorrect full momentum grid")
                    minimum = min(range(51), key=lambda index: row["gaps_mev"][index])
                    if not math.isclose(row["gap_mev"], row["gaps_mev"][minimum], abs_tol=1e-14) or not math.isclose(row["momentum_rad"], row["momenta_rad"][minimum], abs_tol=1e-14):
                        case_errors.append(f"{label}/{scenario_index}: inconsistent reported minimum")
                measured = evaluator.performance(rows)
                anchor.update(
                    **measured,
                    scenario_gaps_mev=[row["gap_mev"] for row in rows],
                    class_d_invariants=[row["class_d_invariant"] for row in rows],
                    scenario_seconds=[row["seconds"] for row in rows],
                )
                anchor["core_feasible"] = bool(geometry_status["valid"] and measured["physical_feasibility"])
                diagnostic[label] = {"geometry": geometry_status, "measurements": rows, **measured}
                if calibration is not None:
                    stored = calibration.get(label, {})
                    if stored.get("measurements") != rows or stored.get("geometry") != geometry_status:
                        case_errors.append(f"{label}: calibration and full checkpoint disagree")
                    for key, value in measured.items():
                        if isinstance(value, bool):
                            equal = stored.get(key) == value
                        else:
                            equal = isinstance(stored.get(key), (int, float)) and math.isclose(stored[key], value, abs_tol=1e-14)
                        if not equal:
                            case_errors.append(f"{label}: inconsistent {key}")
            else:
                anchor["core_feasible"] = None
                diagnostic[label] = {"geometry": geometry_status, "measurements": rows, "physical_feasibility": None, "robust_gap_mev": None, "complete": False}
            record[label] = anchor
        complete = all(record[label]["complete"] for label in ("weak", "strong"))
        record["complete"] = complete
        if complete:
            weak_gap, strong_gap = record["weak"]["robust_gap_mev"], record["strong"]["robust_gap_mev"]
            record["strong_minus_weak_mev"] = strong_gap - weak_gap
            anchors_physical = all(record[label]["core_feasible"] for label in ("weak", "strong"))
            if anchors_physical:
                try:
                    record["anchor_scores"] = {
                        "weak": evaluator.normalized_score(weak_gap, weak_gap, strong_gap),
                        "strong": evaluator.normalized_score(strong_gap, weak_gap, strong_gap),
                    }
                except ValueError as error:
                    record["anchor_rejection_reason"] = str(error)
            else:
                record["anchor_rejection_reason"] = "One or both frozen anchors fail geometry/topology/gap feasibility"
        else:
            record["anchor_rejection_reason"] = "Incomplete full-resolution measurements; not a physical failure"
        if calibration is not None:
            if calibration.get("fingerprint") != expected_fingerprint or calibration.get("momentum_points") != 51 or calibration.get("scoring_rule") != evaluator.SCORING_RULE:
                case_errors.append("Calibration fingerprint/resolution/scoring rule mismatch")
            if calibration.get("ready") and record["anchor_scores"] != calibration.get("anchor_scores"):
                case_errors.append("Saved normalization anchors disagree with unchanged evaluator")
        else:
            diagnostic.update(complete=complete, anchor_rejection_reason=record.get("anchor_rejection_reason", "Evaluator exited before producing a final calibration"))
            save(HERE / f"{case}_diagnostic_calibration.json", diagnostic)
        evaluator_succeeded = bool(output and output.get("complete") and calibration and output.get("cases") == [calibration] and calibration.get("ready"))
        record["reference_gate_pass"] = bool(
            complete and record["anchor_scores"] == {"weak": 0.0, "strong": 1.0}
            and evaluator_succeeded and not case_errors and protected_unchanged
            and execution["cases"].get(case, {}).get("returncode") == 0
        )
        record["validation_errors"] = case_errors
        errors.extend(f"{case}: {error}" for error in case_errors)
        for label in ("weak", "strong"):
            score_records[label].append({
                "request_id": case, "score": record["anchor_scores"][label] if record["reference_gate_pass"] else None,
                "core_feasible": record[label]["core_feasible"],
                "robust_gap_mev": record[label]["robust_gap_mev"],
            })
        case_records.append(record)
    resource_checks = {"samples": 0, "worker_observations": 0, "all_affinities_match": True, "all_observed_worker_threads_one": True, "max_sampled_worker_rss_kib": 0}
    snapshots_path = RUNS / "resource_snapshots.jsonl"
    if snapshots_path.exists():
        for line in snapshots_path.read_text().splitlines():
            snapshot = json.loads(line)
            resource_checks["samples"] += 1
            for case, processes in snapshot["cases"].items():
                root_pid = runtime["commands"][case]["pid"]
                for process in processes:
                    resource_checks["all_affinities_match"] &= process["affinity"] == ASSIGNMENTS[case]
                    if process["pid"] != root_pid:
                        resource_checks["worker_observations"] += 1
                        resource_checks["all_observed_worker_threads_one"] &= process.get("Threads") == "1"
                        rss = int(process.get("VmRSS", "0 kB").split()[0])
                        resource_checks["max_sampled_worker_rss_kib"] = max(resource_checks["max_sampled_worker_rss_kib"], rss)
    if not resource_checks["all_affinities_match"] or not resource_checks["all_observed_worker_threads_one"]:
        errors.append("Observed process affinity or worker thread-count mismatch")
    all_pass = all(record["reference_gate_pass"] for record in case_records) and not errors
    validation = {
        "validated_utc": stamp(), "validation_passed": not errors,
        "all_reference_gates_pass": all_pass, "complete": all(record["complete"] for record in case_records),
        "case_selection_frozen": actual_cases == set(ASSIGNMENTS), "no_cases_dropped_or_resampled": True,
        "protected_inputs_unchanged": protected_unchanged, "no_new_forward_evaluations": True,
        "numeric_wall_seconds": execution["numeric_wall_seconds"], "numeric_wall_budget_seconds": execution["numeric_wall_budget_seconds"],
        "resources": resource_checks, "errors": errors, "cases": case_records,
    }
    save(HERE / "full_calibration_validation.json", validation)
    score_check = {"complete": all_pass, "check_mode": "unchanged evaluator normalization and aggregation on stored full-51 anchor measurements; no forward rerun", "scoring_rule": evaluator.SCORING_RULE}
    for label, records in score_records.items():
        score_check[label] = {"cases": records, "aggregate": evaluator.summarize_scores(records) if all_pass else None}
    save(HERE / "reference_score_check.json", score_check)
    report = [
        "# Frozen ratchet reference calibration", "",
        f"All three preregistered reference gates pass: {all_pass}. Full-calibration validation passes: {not errors}.",
        "No cases were dropped, selected, or resampled after outcomes. No public, case, source-mask, physics, or evaluator files were changed. No confirmation attempt/transcript was accessed.", "",
        "| Case | Warm baseline R (meV) | Source R (meV) | Source minus baseline | Baseline/source scores | Gate |",
        "|---|---|---|---|---|---|",
    ]
    for record in case_records:
        report.append(f"| {record['request_id']} | {record['weak']['robust_gap_mev']} | {record['strong']['robust_gap_mev']} | {record['strong_minus_weak_mev']} | {record['anchor_scores']} | {record['reference_gate_pass']} |")
    report.extend(["", "## Full scenario metrics", "", "| Case | Design | Scenario (mu, EZ), meV | Full-51 gap (meV) | Q | Scenario seconds |", "|---|---|---|---|---|---|"])
    for record in case_records:
        for label in ("weak", "strong"):
            anchor = record[label]
            if anchor["complete"]:
                for scenario, gap, invariant, seconds in zip(record["scenarios"], anchor["scenario_gaps_mev"], anchor["class_d_invariants"], anchor["scenario_seconds"]):
                    report.append(f"| {record['request_id']} | {label} | ({scenario['mu_normal_mev']}, {scenario['zeeman_mev']}) | {gap:.12f} | {invariant} | {seconds:.2f} |")
            else:
                report.append(f"| {record['request_id']} | {label} | incomplete | — | — | — |")
    report.extend([
        "", f"Numerical wall time: {execution['numeric_wall_seconds']:.2f} / {execution['numeric_wall_budget_seconds']:.0f} seconds. CPU sets: lower 64–69, central 72–77, high-density 80–85; three workers per case and one BLAS thread.",
        f"Resource checks: {json.dumps(resource_checks, sort_keys=True)}.", "",
        "R = 0.5 mean(gaps) + 0.5 min(gaps). All gaps use the unchanged 25,608-DOF forward evaluator, full 51 momenta, and an independent Pfaffian Q. The weak reference is the previously achieved frozen public baseline, not the original zigzag.", "",
        "The score check applies the unchanged evaluator to stored full-resolution anchor measurements; it is not a second numerical evaluation or a fresh solver run. Incomplete measurements are not physical failures. Any failed reference gate is grounds for rejection, not case substitution.", "",
        "Full raw calibration/measurement files remain alongside this report; unchanged CLI outputs and logs are in ../reference_runs/. Detailed checks are in full_calibration_validation.json and reference_score_check.json.", "",
    ])
    (HERE / "CALIBRATION_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({key: value for key, value in validation.items() if key != "cases"}, indent=2))
    for record in case_records:
        print(json.dumps({"case": record["request_id"], "weak_R_mev": record["weak"]["robust_gap_mev"], "strong_R_mev": record["strong"]["robust_gap_mev"], "anchor_scores": record["anchor_scores"], "gate": record["reference_gate_pass"]}))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
