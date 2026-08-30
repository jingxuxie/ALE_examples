import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit import ROOT, digest, dump, fc
from refine import verified_source


def main():
    inventory = fc.read_json(HERE / "inventory.json", 8 * 1024 * 1024)
    screening = fc.read_json(HERE / "screening.json", 8 * 1024 * 1024)
    checks = fc.read_json(HERE / "failure_checks.json", 8 * 1024 * 1024)
    assert screening["status"] == checks["status"] == "complete"
    assert screening["screened"] == inventory["counts"]["distinct_valid_controls"]
    alternatives = [row for row in inventory["distinct_controls"] if not row["is_canonical_submission"]]
    assert {row["id"] for row in checks["results"]} == {row["id"] for row in alternatives}
    protocol = fc.read_json(ROOT / "evaluator/hidden/protocol.json")
    cases = fc.read_json(ROOT / "evaluator/hidden/cases.json")
    assert len(cases) == 37
    for candidate in inventory["distinct_controls"]:
        verified_source(candidate)
    for item in inventory["files"]:
        assert item["recorded_sha256"] == digest(ROOT / item["source"])
    for name, expected in inventory["protected_sha256"].items():
        assert digest(ROOT / name) == expected
    for name, expected in checks["reference_sha256"].items():
        assert digest(ROOT / name) == expected
    official = []
    selections = sorted((HERE / "official").glob("selection*.json"))
    selected = set()
    for path in selections:
        selected.update(fc.read_json(path)["selected"])
    for identity in sorted(selected):
        stem = Path(identity).stem
        path = HERE / "official" / (stem + ".evaluation.json")
        result = fc.read_json(path, 4 * 1024 * 1024)
        provenance = fc.read_json(HERE / "official" / (stem + ".provenance.json"))
        assert provenance["evaluation_sha256"] == digest(path)
        candidate = next(row for row in alternatives if row["id"] == identity)
        assert result["artifact_canonical_sha256"] == candidate["canonical_sha256"]
        necessary = next(row for row in checks["results"] if row["id"] == identity)
        matching = next(row for row in result["cases"] if row["id"] == necessary["case"]["id"])
        agreement = abs(matching["audited_fidelity"] - necessary["audited_fidelity"])
        assert agreement < 1e-10
        scores = {key: result[key] for key in ("valid", "passed", "reason", "core_score", "worst_family_score", "worst_case_score", "runtime_seconds", "runtime_score", "resource_score")}
        diagnostic_scores = fc.summarize([row["audited_fidelity"] for row in result["cases"]], cases, protocol)
        diagnostic_scores.pop("passed")
        official.append({"id": identity, "sources": candidate["sources"], "evaluation": str(path.relative_to(HERE)), "evaluation_sha256": digest(path), "artifact_canonical_sha256": candidate["canonical_sha256"], "scores": scores, "fidelity_metrics_before_audit_rejection": diagnostic_scores, "audits": result["audits"], "single_case_full_evaluator_difference": agreement})
    canonical = []
    for tag in ("v_3", "v_4"):
        run_path = ROOT / "attempts" / (tag + ".run.json")
        run = fc.read_json(run_path, 4 * 1024 * 1024)
        assert run.get("status") not in (None, "running")
        path = ROOT / "attempts" / (tag + ".evaluation.json")
        result = fc.read_json(path, 4 * 1024 * 1024)
        candidate = next(row for row in inventory["distinct_controls"] if any(source["path"] == "attempts/" + tag + "/control.json" for source in row["sources"]))
        assert result["artifact_canonical_sha256"] == candidate["canonical_sha256"]
        canonical.append({"attempt": tag, "run_status": run["status"], "run_record_sha256": digest(run_path), "evaluation": str(path.relative_to(ROOT)), "evaluation_sha256": digest(path), "artifact_canonical_sha256": candidate["canonical_sha256"], "scores": {key: result[key] for key in ("valid", "passed", "reason", "core_score", "worst_family_score", "worst_case_score")}})
    passed = [row for row in official + canonical if row["scores"]["passed"]]
    excluded = all(row["frozen_worst_case_threshold_failed"] or row["failed_audits"] for row in checks["results"])
    assert passed or excluded
    report = {"finished_utc": datetime.now(timezone.utc).isoformat(), "audit_role": "privileged_audit_of_original_fresh_generation_2_outputs", "outcome": "original_pre_cutoff_pass_found" if passed else "no_eligible_saved_alternative_passes", "counts": inventory["counts"], "full_case_screen_count": len(cases), "case_screen_combinations": screening["screened"] * len(cases), "refined_alternative_count": checks["count"], "clean_refined_fidelity_failures": sum(row["refined_fidelity_failure_with_allowance_margin"] for row in checks["results"]), "refined_audit_violations": sum(bool(row["failed_audits"]) for row in checks["results"]), "all_selected_refined_fidelities_below_target_even_with_empirical_allowance": all(row["empirical_upper_check"] < protocol["thresholds"]["worst_case_score"] for row in checks["results"]), "largest_selected_empirical_upper_check": max(row["empirical_upper_check"] for row in checks["results"]), "all_eligible_originals_excluded_by_frozen_tests": excluded and not passed and all(not row["scores"]["passed"] for row in canonical), "official_alternatives": official, "canonical_evaluations": canonical, "passing_originals": passed, "new_optimization": False, "coefficient_reconstruction_or_postprocessing": False, "original_bytes_verified_after_grading": True, "protected_files_and_references_unchanged": True, "generation_3_built": False, "champion_archived": False, "main_metadata_modified": False, "classification_authority": "main", "classification_recommendation": "credit_original_witness_and_reconsider_final_ratchet" if passed else "retain_generation_2_hard_verified_achievable", "filename_selection_conclusion": "Canonical v4 underrepresents saved improvements, but no passing exact-schema artifact is hidden by filename selection." if not passed else "Canonical filename selection hid a passing original artifact.", "compute": {"screen_wall_seconds": screening["elapsed_seconds"], "necessary_case_refinement_wall_seconds": checks["elapsed_seconds"], "full_official_grade_count": len(official), "note": "Components overlap; their wall times are not additive elapsed time or measured CPU usage."}}
    dump("conclusion.json", report)
    files = sorted(path for path in HERE.rglob("*") if path.is_file() and path.name != "manifest.json")
    dump("manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "sha256": {str(path.relative_to(HERE)): digest(path) for path in files}, "protected_root_sha256": inventory["protected_sha256"]})
    print(json.dumps({"outcome": report["outcome"], "counts": report["counts"], "clean_refined_fidelity_failures": report["clean_refined_fidelity_failures"], "refined_audit_violations": report["refined_audit_violations"], "official": [{"id": row["id"], **row["scores"]} for row in official]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
