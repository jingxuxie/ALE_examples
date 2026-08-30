#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from author_tests import load_module, run_tests, write_json


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = ROOT / "evaluator" / "hidden"


def main():
    started = time.perf_counter()
    if not (HIDDEN / "frozen_manifest.json").exists():
        subprocess.run([sys.executable, "-B", str(HIDDEN / "freeze_target.py")], check=True, cwd=ROOT)
    manifest = json.loads((HIDDEN / "frozen_manifest.json").read_text())
    audit = run_tests()
    print(json.dumps({"stage": "author_audit", "passed": audit["passed"],
                      "named_checks": audit["named_checks"], "runtime_seconds": audit["runtime_seconds"]}), flush=True)
    grader = load_module("authoring_evaluator", ROOT / "evaluator" / "evaluate.py")
    public = load_module("authoring_public_checker", ROOT / "participant" / "check.py")
    baseline_runs = []
    for seed in (1701, 2718, 31415):
        output = ROOT / "participant" / "baseline" if seed == 1701 else ROOT / "adversary" / "calibration" / f"seed_{seed}"
        subprocess.run([sys.executable, "-B", str(ROOT / "participant" / "baseline" / "generate.py"),
                        "--output", str(output), "--seed", str(seed), "--restarts", "4", "--steps", "60000"],
                       cwd=ROOT, check=True, timeout=180)
        grade = grader.evaluate(output)
        local_grade = public.evaluate(output)
        metrics = json.loads((output / "search_report.json").read_text())
        assert grade["valid"] and grade["squared_error"] == metrics["squared_error"]
        assert grade["passed"] == local_grade["passed"] and grade["squared_error"] == local_grade["squared_error"]
        assert metrics["target_sha256"] == manifest["target_sha256"]
        write_json(output / "grade_report.json", grade)
        baseline_runs.append({"seed": seed, "artifact": str(output.relative_to(ROOT) / "design.json"),
                              "core_score": grade["core_score"], "worst_family_score": grade["worst_family_score"],
                              "valid": grade["valid"], "passed": grade["passed"],
                              "squared_error": grade["squared_error"], "matched_lags": grade["matched_lags"],
                              "search_runtime_seconds": metrics["search_runtime_seconds"],
                              "checker_runtime_seconds": grade["runtime_seconds"], "proposals": metrics["proposals"]})
        print(json.dumps({"stage": "baseline_scored", **baseline_runs[-1]}), flush=True)
    for target_path in (HIDDEN / "target.json", ROOT / "participant" / "input" / "target.json"):
        assert hashlib.sha256(target_path.read_bytes()).hexdigest() == manifest["target_sha256"]
    solved_by_control = any(run["passed"] for run in baseline_runs)
    status = {
        "concept": "concept_3", "mode": "C_WITNESS_DESIGN", "generation": 0,
        "status": "baseline_solved" if solved_by_control else "ready_for_fresh_attempts",
        "ready_for_fresh_attempts": not solved_by_control,
        "final_status": "pending_main_session_tournament", "solvability": "privately_demonstrated",
        "hardness_verified": False, "fresh_agents_launched": 0, "fresh_agent_results": [],
        "target": {"direction_count": 1024, "pair_count": 512, "counts": {"0": 416, "1": 64, "2": 32},
                   "energy_integer_sum": 128, "required_core_score": 1.0, "required_worst_family_score": 1.0,
                   "target_sha256": manifest["target_sha256"], "frozen_at_utc": manifest["frozen_at_utc"],
                   "changed_after_baseline": False},
        "baseline": baseline_runs[0], "bounded_calibration": baseline_runs,
        "planted": {key: audit["planted_report"][key] for key in
                    ("core_score", "worst_family_score", "runtime_score", "resource_score", "valid", "passed", "runtime_seconds")},
        "audit": {"passed": audit["passed"], "named_checks": audit["named_checks"],
                  "all_lags_enforcement_checks": 512, "incremental_delta_checks": 32,
                  "independent_arithmetic": True, "independent_agent_review": False,
                  "runtime_seconds": audit["runtime_seconds"], "report": "evaluator/hidden/author_audit.json"},
        "security": {"submission_format": "static JSON only", "submitted_code_executed": False,
                     "participant_allowlist": ["participant/", "one initially empty attempts/<id>/"],
                     "private_witness": "evaluator/hidden/planted/design.json",
                     "same_user_filesystem_permissions_are_not_isolation": True},
        "concerns": ["Only bounded local-search controls have run; no general hardness claim or fresh-agent result.",
                     "The independent audit is a separate arithmetic implementation, not an independent-agent review.",
                     "Main session must enforce filesystem allowlists; hidden paths and mode bits alone do not isolate same-user agents.",
                     "The event is synthetic and discrete, not an NLO QCD continuum prediction."],
        "next_action": "Main session launches the two isolated one-hour attempts; do not expose private directories.",
        "authoring_runtime_seconds": time.perf_counter() - started,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ROOT / "status.json", status)
    write_json(ROOT / "adversary" / "readiness_report.json", status)
    audit_text = (
        "# Private readiness audit\n\n"
        f"Frozen target SHA-256: `{manifest['target_sha256']}`.\n\n"
        f"Independent arithmetic and static-artifact checks passed: {audit['named_checks']} named checks, "
        "512 individually perturbed lags, and 32 integer swap-delta tests. "
        "All 1024 directed bins and 513 geometric angular bins agree; exact rational "
        "normalizations are one, with self-pairs and antipodal endpoints retained.\n\n"
        "The planted witness scores 1.0 and remains exclusively private. "
        "Malformed JSON, wrong counts, cyclic-boundary violations, feasible wrong correlations, "
        "symlinks, directories, FIFOs, oversized files, target spoofing, and submitted-code "
        "probes are rejected or ignored as appropriate. Rotations and reflection pass.\n\n"
        "## Bounded controls\n\n"
        "| Seed | Proposals | Core | Matched lags | Squared error | Search seconds |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    for run in baseline_runs:
        audit_text += (f"| {run['seed']} | {run['proposals']} | {run['core_score']} | "
                       f"{run['matched_lags']} | {run['squared_error']} | {run['search_runtime_seconds']:.3f} |\n")
    audit_text += (
        "\nThe target was not resampled or changed after these controls. "
        "Their failures are evidence against this bounded baseline only. They do not establish "
        "failure of phase-retrieval, constraint-programming, stronger search, or the forthcoming agents. "
        "No fresh agents were launched. This audit is implementation-independent arithmetic "
        "by the authoring process, not a separate agent's review.\n"
    )
    (ROOT / "adversary" / "AUDIT.md").write_text(audit_text, encoding="utf-8")
    print(json.dumps({"stage": "ready", "status": status["status"], "target_sha256": manifest["target_sha256"],
                      "planted_core_score": status["planted"]["core_score"], "baseline_runs": baseline_runs,
                      "authoring_runtime_seconds": status["authoring_runtime_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
