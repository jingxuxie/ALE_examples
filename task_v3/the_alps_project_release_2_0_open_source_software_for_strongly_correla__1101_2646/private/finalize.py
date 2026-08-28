import datetime
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ["c01_stats", "c02_dmft", "c03_mps", "c04_continuation"]


def read_json(path):
    return json.loads(path.read_text())


def snapshot(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def dictionaries(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)


def main():
    summaries = {}
    audit = {}
    total_cases = 0
    for name in CONCEPTS:
        concept = ROOT / name
        run = read_json(concept / "private" / "runs" / "initial.json")
        checks = {"requested_model": run["model"] == "ultima-alpha", "completed_normally": run["returncode"] == 0,
                  "within_pilot_limit": run["elapsed_seconds"] <= 3600,
                  "initially_empty_attempt": run["empty_attempt_verified"],
                  "participant_unchanged": run["participant_before"] == run["participant_after"] == snapshot(concept / "participant")}
        source_hashes = {path: digest for path, digest in run["deliverables"].items()
                         if Path(path).suffix in {".py", ".c", ".cc", ".cpp", ".h", ".hpp", ".so"}}
        checks["submitted_code_unchanged"] = all((concept / "attempt" / path).is_file()
                                                and hashlib.sha256((concept / "attempt" / path).read_bytes()).hexdigest() == digest
                                                for path, digest in source_hashes.items())
        checks["paper_free_TASK"] = not any(word in (concept / "participant" / "TASK.md").read_text().lower()
                                            for word in ["1101.2646", "arxiv", "alps project"])
        assert all(checks.values()), (name, checks)
        audit[name] = checks
        stages = {}
        all_cases = []
        peak_memory = 0
        max_wall = 0.0
        for split in ["core", "challenge", "stress"]:
            report_path = concept / "private" / "runs" / f"initial_{split}.json"
            if not report_path.exists():
                continue
            report = read_json(report_path)
            cases = report["cases"]
            assert all(case["score"] >= 0.90 for case in cases), (name, split, "a case needs further investigation")
            assert report["worst_family_score"] >= 0.90
            stages[split] = {"mean_core_score": report["mean_core_score"], "worst_family_score": report["worst_family_score"],
                             "case_count": len(cases), "families": report["families"], "report": str(report_path.relative_to(ROOT))}
            all_cases.extend(cases)
            for case in cases:
                for record in dictionaries(case):
                    if isinstance(record.get("max_rss_kib"), (int, float)):
                        peak_memory = max(peak_memory, record["max_rss_kib"])
                    for key in ["seconds", "wall_seconds", "evaluator_wall_seconds", "resource_seconds"]:
                        if isinstance(record.get(key), (int, float)):
                            max_wall = max(max_wall, record[key])
        total_cases += len(all_cases)
        summaries[name] = {"decision": "rejected_solved", "model": run["model"], "pilot_seconds": run["elapsed_seconds"],
                           "stages": stages, "all_case_mean": sum(case["score"] for case in all_cases) / len(all_cases),
                           "worst_case_score": min(case["score"] for case in all_cases),
                           "worst_reported_family_score": min(stage["worst_family_score"] for stage in stages.values()),
                           "max_case_wall_seconds": max_wall, "peak_rss_mib": peak_memory / 1024,
                           "ratchets_built": 0, "second_fresh_attempts": 0}
    assert total_cases == 70, total_cases
    specification = importlib.util.spec_from_file_location("mps_evaluator_audit", ROOT / "c03_mps" / "private" / "evaluator.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    mps_private = ROOT / "c03_mps" / "private"
    manifest = read_json(mps_private / "challenge_pool" / "manifest.json")
    lower_chi_scores = {}
    for entries in manifest["splits"].values():
        for entry in entries:
            case = read_json(mps_private / entry["input"])
            reference = read_json(mps_private / entry["reference"])
            assert reference["ready"]
            lower = reference["convergence"]["history"][0]["result"]
            score, _ = evaluator.score_output(case, reference["reference"], reference["weak"], lower)
            lower_chi_scores[entry["id"]] = score
    assert min(lower_chi_scores.values()) > 0.90
    audit["mps_lower_chi_against_strong_reference"] = lower_chi_scores
    audit["all_70_cases_above_solved_threshold"] = True
    audit["reference_evidence"] = {
        "c01": "c01_stats/private/readiness.json",
        "c02": "c02_dmft/private/reference/validation_summary.json",
        "c03": "c03_mps/private/reference/validation/readiness.json",
        "c03_stress": "c03_mps/private/reference/stress_audit.json",
        "c04": "c04_continuation/private/reference/band_grid_validation.json",
        "c04_stress": "c04_continuation/private/challenge_pool/stress.json"}
    supplement = ROOT / "private" / "sources" / "supplement_audit"
    target_audit = read_json(supplement / "target_source_audit.json")
    archive_audit = read_json(supplement / "mps_hdf5_audit.json")
    assert target_audit["original_paper_already_includes_jackknife_and_cross_correlations"]
    assert len(target_audit["ancillary_workflows"]) == 3
    assert archive_audit["verdict"] == "NO_GO_FOR_FRESH_WITHIN_C03_PHYSICAL_HELDOUTS_FROM_THIS_ARCHIVE"
    assert archive_audit["physical_coverage"]["unique_hamiltonian_sector_count"] == 1
    assert not archive_audit["physical_coverage"]["within_c03_contract"]
    assert not archive_audit["checkpoint_audit"]["bundled_mps_checkpoints"]
    archive_path = supplement / archive_audit["sources"]["archive"]
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == archive_audit["sources"]["archive_sha256"]
    assert len(archive_audit["files"]) == 7
    assert all(hashlib.sha256((supplement / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]
               for entry in archive_audit["files"])
    audit["late_source_audit"] = {
        "target_paper_and_three_ancillary_files_inspected": True,
        "original_jackknife_attribution_corrected": True,
        "linked_author_archive_and_seven_hdf5_hashes_verified": True,
        "distinct_hamiltonian_sectors": 1,
        "bundled_mps_checkpoints": False,
        "within_frozen_mps_contract": False,
        "creates_valid_counterexample_or_fresh_physical_holdouts": False,
        "target_evidence": "private/sources/supplement_audit/target_source_audit.json",
        "hdf5_evidence": "private/sources/supplement_audit/mps_hdf5_audit.json",
        "hdf5_report": "private/sources/supplement_audit/MPS_HDF5_AUDIT.md"}
    source_ledger = read_json(ROOT / "private" / "source_ledger.json")
    assert all(hashlib.sha256((ROOT / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]
               for entry in source_ledger if "file" in entry)
    audit["source_ledger_file_hashes_verified"] = True
    ranking = sorted(CONCEPTS, key=lambda name: (summaries[name]["worst_reported_family_score"], summaries[name]["all_case_mean"]))
    result = {"status": "rejected_no_frontier_hard_candidate", "accepted_task": None, "paper_id": "1101.2646",
              "finalized_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "concepts_built": 4,
              "fresh_initial_attempts": 4, "pilot_model": "ultima-alpha", "pilot_limit_seconds": 3600,
              "distinct_hidden_cases_evaluated": total_cases, "ratchets_built": 0, "second_fresh_attempts": 0,
              "reason": "Every initial submission solves every tested hidden family, including source-grounded critical-chain and intrinsically complex-band extensions. No reference-success/submission-failure region justifies a ratchet. None meets the required fresh-agent score below 0.70.",
              "ranking_lowest_worst_family_first": ranking, "concepts": summaries,
              "confirmation_note": "Resource-instrumented re-evaluations are repeated grading of the same frozen submissions, not additional fresh agents. Phase-7 fresh tests are inapplicable after rejection for absence of a meaningful counterexample.",
              "late_source_audit": audit["late_source_audit"],
              "report": "REPORT.md", "candidate_record": "CANDIDATES.md"}
    (ROOT / "selection.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (ROOT / "private" / "FINAL_AUDIT.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "case_count": total_cases, "ranking": ranking,
                      "minimum_reference_crosscheck_score": min(lower_chi_scores.values()),
                      "resources": {name: {key: value for key, value in summary.items() if key in ["max_case_wall_seconds", "peak_rss_mib"]}
                                    for name, summary in summaries.items()}}, indent=2))


if __name__ == "__main__":
    main()
