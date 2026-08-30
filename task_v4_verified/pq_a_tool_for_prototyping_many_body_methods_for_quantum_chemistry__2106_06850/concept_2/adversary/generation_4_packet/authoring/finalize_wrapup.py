"""Record shutdown and final trusted scores without running further search."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
AUTHORING = PACKET / "authoring"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owned-jobs", required=True)
    arguments = parser.parse_args()
    if arguments.owned_jobs.strip():
        raise RuntimeError("owned private jobs remain active")
    checks = {}
    for name in ("freeze.json", "evaluator_freeze.json"):
        manifest = json.loads((PACKET / name).read_text())
        for relative, digest in manifest["sha256"].items():
            checks[relative] = hashlib.sha256((PACKET / relative).read_bytes()).hexdigest() == digest
    if not all(checks.values()):
        raise RuntimeError("frozen source hash mismatch")
    investigation = json.loads((AUTHORING / "investigation_report.json").read_text())
    portfolio = json.loads((AUTHORING / "portfolio_certification_final.json").read_text())
    records = portfolio["records"]
    proof = json.loads((AUTHORING / "exact_relaxed_state_exclusion.json").read_text())
    report = {"wrapup_at_utc": datetime.now(timezone.utc).isoformat(),
              "search_completed_at_utc": investigation["completed_at_utc"],
              "investigation_wall_minutes": investigation["elapsed_wall_minutes"],
              "owned_private_jobs_running": 0, "additional_search_during_wrapup": False,
              "feasibility": "unknown", "best_trusted_core_score": max(record["core_score"] for record in records),
              "passing_witness_found": any(record["passed"] for record in records),
              "universal_obstruction_proved": False, "global_relaxation_bound_proved": False,
              "fixed_tuple_exact_sign_certificate_passed": proof["passed"],
              "fixed_tuple_certificate_is_not_a_universal_task_proof": True,
              "state_relaxation_multistarts": sum(record["starts"] for record in investigation["relaxation_runs"].values()),
              "independent_artifacts": len(records),
              "independent_endpoint_evaluations": sum(record["coverage"]["evaluated_points"] for record in records),
              "path_certificates_evaluated": sum(record["coverage"]["path_certificates_evaluated"] for record in records),
              "all_endpoint_failures_earn_zero": all(record["core_score"] == 0 for record in records),
              "trusted_records": records, "frozen_files_rechecked": len(checks), "frozen_hashes_match": True,
              "active_fresh_attempt_data_read": False, "agents_launched": 0,
              "main_status_modified": False, "main_empirical_status_decision_reserved": True}
    (AUTHORING / "FINAL_AUDIT.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: report[key] for key in ("feasibility", "best_trusted_core_score", "passing_witness_found",
        "universal_obstruction_proved", "owned_private_jobs_running", "state_relaxation_multistarts",
        "independent_endpoint_evaluations", "path_certificates_evaluated", "frozen_hashes_match")}, indent=2))


if __name__ == "__main__":
    main()
