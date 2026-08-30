from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
ARCHIVE = ROOT / "adversary/generation_3_snapshot_before_cpu_repair"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((AREA / name).read_text())


def main():
    prepared = load("promotion_provenance.json")
    current_manifest = ROOT / "evaluator/hidden/manifest.json"
    archive_manifest = ARCHIVE / "evaluator/hidden/manifest.json"
    assert digest(current_manifest) == prepared["staged_manifest_sha256"]
    assert digest(archive_manifest) == prepared["source_manifest_sha256"]
    original = json.loads(archive_manifest.read_text())
    current = json.loads(current_manifest.read_text())
    for relative, expected in original["files"].items():
        assert digest(ARCHIVE / relative) == expected
        if relative not in prepared["changed_paths"]:
            assert digest(ROOT / relative) == expected
    for relative, expected in current["files"].items():
        assert digest(ROOT / relative) == expected
    for relative, expected in prepared["staged_file_sha256"].items():
        assert digest(ROOT / relative) == expected
    report_names = ("promoted_cli_selfcheck_report.json", "promoted_cli_baseline_report.json",
                    "promoted_resources_report.json", "promoted_audit_report.json",
                    "family_portfolio_official_cgroup_report.json")
    reports = {name: load(name) for name in report_names}
    checks = reports[report_names[0]]
    baseline = reports[report_names[1]]
    resources = reports[report_names[2]]
    compatibility = reports[report_names[3]]
    portfolio = reports[report_names[4]]
    assert checks["passed"] and checks["self_checks_passed"] == 56
    assert resources["passed"] and resources["resource_checks_passed"] == 9
    assert compatibility["passed"]
    assert baseline["valid"] and len(baseline["episodes"]) == 12
    assert baseline["average_family_score"] == .13310665517831277
    assert baseline["worst_family_score"] == .10894424774926101
    for report in (resources, compatibility):
        for relative, expected in report["promoted_code_sha256"].items():
            assert digest(ROOT / relative) == expected
    for report in (baseline, portfolio):
        assert report["manifest_sha256"] == digest(current_manifest)
        assert report["valid"] and len(report["episodes"]) == 12
        assert all(record["process_isolation"] == "bwrap" and
                   record["cpu_accounting"]["source"] == "cgroup_v2_cpu.stat" and
                   record["cpu_accounting"]["owned_episode_cgroup_removed"]
                   for record in report["episodes"])
    selection_audit = json.loads((AREA.parent / "final_audit.json").read_text())
    portfolio_path = AREA.parent / "policies/family_portfolio"
    for filename, expected in selection_audit["selection"]["policy_files_sha256"].items():
        assert digest(portfolio_path / filename) == expected
    boundary = load("cgroup_boundary_report.json")
    for filename in ("model.py", "transport.py", "selfcheck.py", "cgroup_accounting.py"):
        assert digest(ROOT / "evaluator/hidden" / filename) == boundary["private_runtime_sha256"][filename]
    correction = {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "promoted": True,
        "generation": 3,
        "extra_generation_or_ratchet": False,
        "clearance": "Main confirmed v3 completion, deadline hash preservation, and immutable pre-repair archival before authorizing promotion.",
        "archive": str(ARCHIVE.relative_to(ROOT)),
        "source_manifest_sha256": digest(archive_manifest),
        "corrected_manifest_sha256": digest(current_manifest),
        "patch_sha256": digest(AREA / "promotion.patch"),
        "changed_paths": prepared["changed_paths"],
        "corrected_file_sha256": prepared["staged_file_sha256"],
        "protected_original_files_unchanged": True,
        "attempts_champions_snapshots_and_root_status_not_modified": True,
        "old_bug": "Outer bubblewrap RUSAGE_CHILDREN omitted policy descendants. A real 62.207089-self-CPU fork workload was valid with only 0.175025 reported CPU.",
        "old_test_gap": "The original 56 checks did not test real multiprocess CPU. The separate old aggregate test mocked RUSAGE_CHILDREN; it was not an aggregate-enforcement proof.",
        "repair": "Trusted evaluator auto-bootstraps into an owned user service when needed. Each bwrap process tree enters its own cgroup before launch; kernel cpu.stat supplies the aggregate CPU, including threads, ignored SIGCHLD and SA_NOCLDWAIT. Unavailable counters fail closed.",
        "unchanged_contract": "2000 shots; same model, benchmark seeds, priors, targets and quality thresholds; 60 aggregate CPU with existing 0.25 accounting tolerance and 90 wall seconds; all original per-process limits unchanged.",
        "audit_mode": "Explicitly unsafe public development remains usable without cgroup filesystem or user bus, labels RUSAGE_CHILDREN inexact, and never certifies.",
        "validation_report_sha256": {name: digest(AREA / name) for name in report_names},
        "self_checks_passed": checks["self_checks_passed"],
        "real_resource_checks_passed": resources["resource_checks_passed"],
        "public_audit_compatibility_passed": compatibility["passed"],
        "baseline_valid_episodes": len(baseline["episodes"]),
        "baseline_average_worst": [baseline["average_family_score"], baseline["worst_family_score"]],
        "boundary_proof_reused_only_after_exact_final_runtime_hash_match": True,
        "staged_cleanup_failure": {
            "report": "staged_cli_baseline_report.json",
            "sha256": digest(AREA / "staged_cli_baseline_report.json"),
            "description": "One staged baseline episode could not empty its killed cgroup within five seconds and failed closed. Cause not established; retained as infrastructure evidence, not hardness. All twelve separately run promoted baseline episodes were valid without any intervening code change."
        },
        "historical_resource_annotation": {
            "generations_1_and_2": "Historical outer-RUSAGE_CHILDREN CPU numbers are inexact and are not aggregate CPU certificates. Raw archives and core scores remain unchanged.",
            "main_source_review": "Main reports no process-creation API calls in delivered Python/C++ sources, with recorded maximum episode walls 37.06s and 49.42s, respectively. This is a source/runtime observation, not retroactive kernel CPU measurement.",
            "generation_3_pre_repair_private_confirmation": "Its old CPU fields have the same undercount caveat; quality results are retained without retroactive resource certification."
        }
    }
    outcome = {
        "recorded_utc": correction["recorded_utc"],
        "policy": str((portfolio_path / "policy.py").relative_to(ROOT)),
        "policy_files_sha256": selection_audit["selection"]["policy_files_sha256"],
        "unchanged_since_pre_confirmation_selection": True,
        "no_further_optimization": True,
        "budget": 2000,
        "quality_targets": {"average": .5, "worst_family": 1 / 2.5625},
        "official_report": "family_portfolio_official_cgroup_report.json",
        "official_report_sha256": digest(AREA / "family_portfolio_official_cgroup_report.json"),
        "official_valid": portfolio["valid"],
        "official_passed": portfolio["passed"],
        "official_average_worst": [portfolio["average_family_score"], portfolio["worst_family_score"]],
        "official_families": portfolio["families"],
        "official_max_cpu_seconds": max(record["cpu_seconds"] for record in portfolio["episodes"]),
        "official_max_wall_seconds": max(record["wall_seconds"] for record in portfolio["episodes"]),
        "independent_24_case_average_worst": [.4262856900899512, .338483844937249],
        "matched_adapted_g2_control_24_case_average_worst": [.3709446745411399, .30826237667156575],
        "weak_baseline_official_average_worst": correction["baseline_average_worst"],
        "achievability": "demonstrated_by_this_policy" if portfolio["passed"] else "unknown; this fixed-suite valid policy and its independent confirmation both miss the unchanged targets",
        "no_impossibility_claim": True,
        "resource_bug_is_not_hardness": True,
        "fresh_v3_not_read_or_scored_by_this_worker": True,
        "search_closed": True,
        "further_generations": False
    }
    (AREA / "promotion_audit.json").write_text(json.dumps(correction, indent=2) + "\n")
    (AREA / "selected_policy_official_outcome.json").write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps({"promoted": True, "all_required_checks_passed": True,
                      "portfolio_valid": portfolio["valid"], "portfolio_passed": portfolio["passed"],
                      "manifest_sha256": digest(current_manifest)}))


if __name__ == "__main__":
    main()
