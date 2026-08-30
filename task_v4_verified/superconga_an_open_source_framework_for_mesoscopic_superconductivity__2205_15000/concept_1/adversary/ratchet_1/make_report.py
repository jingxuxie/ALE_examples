from common import ROOT, CONCEPT, checked_field, energy_gradient, read_case, write_json

from datetime import datetime, timezone

from focused import FOCUS, aggregate, digest, load
from evaluate import score_field


def main():
    manifest, target = load()
    broad = read_case(ROOT / "analysis.json")
    validation = read_case(ROOT / "validation.json")
    focused_validation = read_case(ROOT / "focused_validation.json")
    qualified = read_case(FOCUS / "qualified_challenger_score.json")
    probe = read_case(ROOT / "runs/accounting_probe_1/score.json")
    repeats = [read_case(ROOT / "runs" / ("focused_champion_cpu_" + str(repeat)) / "score.json") for repeat in (1, 2)]
    if not validation["passed"] or not focused_validation["passed"]:
        raise ValueError("validation failed")
    if not qualified["valid"] or not qualified["passed"]:
        raise ValueError("no qualified executable")
    if not probe["valid"]:
        raise ValueError("accounting protection probe failed")
    if any(not report["valid"] or report["passed"] for report in repeats):
        raise ValueError("champion repeat invalid or target met: proposal needs review")
    repeated_records = [record for report in repeats for record in report["cases"]]
    for repeat in (1, 2):
        for reference in manifest["cases"]:
            record = next(item for item in repeats[repeat - 1]["cases"] if item["case_id"] == reference["case_id"])
            case = read_case(ROOT / reference["case_path"])
            field = checked_field(ROOT / "runs" / ("focused_champion_cpu_" + str(repeat)) / reference["case_id"] / "field.npz", case)
            energy, unused, rms = energy_gradient(case, field)
            if abs(energy - record["checked_energy"]) > 1e-9 or rms > target["stationarity_rms_max"]:
                raise ValueError("champion replay field failed independent recheck")
    rows = []
    extended_scores = []
    for reference in manifest["cases"]:
        name = reference["case_id"]
        meta = read_case(ROOT / "metadata" / (name + ".json"))
        changes = reference["topology"]["changed_hole_windings"]
        replay = [next(record for record in report["cases"] if record["case_id"] == name) for report in repeats]
        row = {
            "case_id": name,
            "shape": meta["shape"],
            "active_sites": meta["active_sites"],
            "holes": meta["actual_holes"],
            "pins": len(meta["pins"]),
            "baseline_energy": reference["baseline_energy"],
            "witness_energy": reference["witness_energy"],
            "gap": reference["gap"],
            "energy_at_65_percent_closure": reference["baseline_energy"] - 0.65 * reference["gap"],
            "baseline_gradient_rms": reference["baseline_gradient_rms"],
            "witness_gradient_rms": reference["witness_gradient_rms"],
            "changed_hole_windings": len(changes),
            "reliable_hole_contours": reference["topology"]["reliable_hole_contours"],
            "minimum_changed_contour_amplitude": min(min(change["baseline_contour_minimum_amplitude"], change["witness_contour_minimum_amplitude"]) for change in changes),
            "replay_energies": [record["checked_energy"] for record in replay],
            "replay_scores": [record["case_score"] for record in replay],
            "best_replay_remaining_gap": min(record["checked_energy"] for record in replay) - reference["witness_energy"],
        }
        path = ROOT / "runs/extended_champion_180" / name / "record.json"
        if path.exists():
            raw = read_case(path)
            case = read_case(ROOT / reference["case_path"])
            field = checked_field(path.parent / "field.npz", case)
            energy, unused, rms = energy_gradient(case, field)
            extended = score_field(reference, case, field, 0.0, target)
            extended["runtime_score"] = 0.0
            extended_scores.append(extended)
            row["extended_champion_diagnostic"] = {"energy": energy, "gradient_rms": rms, "case_score": extended["case_score"], "wall_seconds": raw.get("wall_seconds"), "resource_qualified": False, "source": str(path.relative_to(ROOT))}
        rows.append(row)
    broad_summary = {key: value for key, value in broad.items() if key != "records"}
    broad_summary["old_family_cardinality_readiness_is_superseded"] = True
    counts = {}
    for label in ("champion_cold", "champion_warm", "combined_210", "loop_joint_150"):
        count = sum(read_case(path).get("valid", False) for path in (ROOT / "runs" / label).glob("*/record.json"))
        counts[label] = count
    accountings = [record["resource_accounting"] for record in repeated_records]
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_main_integration_with_explicit_load_caveat",
        "scientific_validation_passed": True,
        "public_and_private_hashes_frozen": True,
        "strict_low_load_validation_complete": False,
        "load_caveat": "The six repeats are sequential, one-core, resource-valid, with trusted payload CPU accounting. CPU/wall ranges show residual scheduling contention and SMT siblings were often busy. Do not describe the entire set as clean low-load repetitions. Main must accept this limitation or obtain controlled low-load confirmation before relying on that stronger claim.",
        "source_broad_search": broad_summary,
        "run_counts_from_per_case_records_not_overwritten_batch_summaries": counts,
        "proposal": "focused_proposal/manifest.json",
        "target": target,
        "proposal_manifest_sha256": digest(FOCUS / "manifest.json"),
        "baseline_contract": "Exact supplied initial field independently attains B on every input; zero closure is reproducible regardless of runtime. Unchanged champion replays are separate evidence, not replacements for B.",
        "baseline_score": {"valid": True, "core_score": 0.0, "worst_family_score": 0.0, "passed": False},
        "champion_repeats": [{key: report[key] for key in ("valid", "status", "core_score", "worst_family_score", "runtime_score", "passed", "reason")} for report in repeats],
        "champion_repeat_reports": ["runs/focused_champion_cpu_1/score.json", "runs/focused_champion_cpu_2/score.json"],
        "replay_wall_range": [min(item["wall_seconds"] for item in accountings), max(item["wall_seconds"] for item in accountings)],
        "replay_cpu_range": [min(item["cpu_seconds"] for item in accountings), max(item["cpu_seconds"] for item in accountings)],
        "replay_cpu_to_wall_range": [min(item["cpu_to_wall_ratio"] for item in accountings), max(item["cpu_to_wall_ratio"] for item in accountings)],
        "qualified_solver": {"entrypoint": "challenger/solve.py", "required_sibling": "challenger/engine.py", "score_report": "focused_proposal/qualified_challenger_score.json", "core_score": qualified["core_score"], "worst_family_score": qualified["worst_family_score"], "runtime_score": qualified["runtime_score"], "valid": qualified["valid"], "passed": qualified["passed"], "source_sha256": qualified["source_sha256"], "resource_evidence": "Actual independent same-budget sandbox outputs on byte-identical inputs, all under 54 seconds; same one-core affinity and hard 60-second CPU limits. Reaggregation is not a new run. No private witness lookup.", "new_protected_cpu_monitor_used_in_this_older_qualification": False},
        "offline_witness_feasibility_score": 1.0,
        "offline_witness_feasibility_is_not_resource_solvability_proof": True,
        "known_achievable_status": "verified_resource_bounded_executable_on_the_frozen_three_cases; not a proof of global optimality or generalization to unseen families",
        "cases": rows,
        "validation": {"physical_numerical": "validation.json", "physical_case_count": validation["case_count"], "checks_per_case": validation["checks_per_case"], "focused_evaluator_tests": "focused_validation.json", "focused_test_count": focused_validation["tests_run"], "protected_cpu_channel_probe": "runs/accounting_probe_1/score.json", "protected_cpu_channel_probe_valid": probe["valid"], "local_polish": "local_polish.json"},
        "public_assets": "candidate_public",
        "public_manifest": "candidate_public_manifest.json",
        "fresh_sessions_launched": 0,
        "scope": "All builder writes confined to concept_1/adversary/ratchet_1. Main owns integration and fresh launches.",
    }
    if len(extended_scores) == target["case_count"]:
        report["extended_champion_quality_only"] = aggregate(extended_scores, target)
        report["extended_champion_quality_only"]["resource_qualified"] = False
        report["extended_champion_quality_only"]["note"] = "180-second privileged diagnostic, not a resource-contract run; scoring here isolates energy quality and uses no timing credit. Does not replace the missing clean-low-load repeat condition."
    write_json(ROOT / "report.json", report)
    status = {key: report[key] for key in ("created_at", "status", "scientific_validation_passed", "public_and_private_hashes_frozen", "strict_low_load_validation_complete", "known_achievable_status", "fresh_sessions_launched")}
    status.update({"valid": True, "approval_required": True, "ready_for_main_review_and_integration": True, "ready_for_unqualified_clean_low_load_claim": False, "report": "report.json", "manifest": "focused_proposal/manifest.json", "manifest_sha256": report["proposal_manifest_sha256"], "public_tree": "candidate_public", "qualified_challenger": "challenger/solve.py", "core_min": target["core_min"], "worst_family_min": target["worst_family_min"], "case_count": target["case_count"], "family_cardinality": target["family_cardinality"]})
    write_json(ROOT / "status.json", status)
    files = [ROOT / name for name in ("report.json", "status.json", "REPORT.md", "INTEGRATION.md", "focused.py", "common.py", "cpu_monitor/run.py", "challenger/solve.py", "challenger/engine.py", "baseline/solve.py", "test_focused.py", "validation.json", "focused_validation.json", "local_polish.json", "candidate_public_manifest.json")]
    files.extend(path for path in FOCUS.rglob("*") if path.is_file())
    files.extend(path for path in (ROOT / "candidate_public").rglob("*") if path.is_file())
    for label in ("focused_champion_cpu_1", "focused_champion_cpu_2", "accounting_probe_1", "proposal_challenger", "extended_champion_180"):
        files.extend(path for path in (ROOT / "runs" / label).rglob("*") if path.is_file())
    write_json(ROOT / "packet_manifest.json", {"created_at": report["created_at"], "status": status["status"], "files": {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(files)) if path.exists()}, "scoring_target_is_immutable": True, "private_packet_not_for_participant_mount": True})
    print(status)


if __name__ == "__main__":
    main()
