#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from author_audit import load_module, run_audit, write_json


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = ROOT / "evaluator/hidden"


def main():
    started = time.perf_counter()
    active_root = ROOT.parents[1]
    active_paths = ["participant/TASK.md", "participant/check.py", "participant/input/target.json",
                    "participant/input/design.schema.json", "participant/baseline/generate.py",
                    "evaluator/evaluate.py", "evaluator/hidden/target.json", "evaluator/hidden/frozen_manifest.json"]
    active_hashes = {name: hashlib.sha256((active_root / name).read_bytes()).hexdigest() for name in active_paths}
    if not (HIDDEN / "frozen_manifest.json").exists():
        subprocess.run([sys.executable, "-B", str(HIDDEN / "freeze_target.py")], check=True, cwd=ROOT)
    manifest = json.loads((HIDDEN / "frozen_manifest.json").read_text())
    audit = run_audit()
    print(json.dumps({"stage": "scaled_author_audit", "passed": audit["passed"],
                      "named_checks": audit["named_checks"], "runtime_seconds": audit["runtime_seconds"]}), flush=True)
    output = ROOT / "participant/baseline"
    subprocess.run([sys.executable, "-B", str(output / "generate.py"), "--output", str(output),
                    "--seed", "1701", "--restarts", "4", "--steps", "60000"], check=True, cwd=ROOT, timeout=150)
    grader = load_module("readiness_grader", ROOT / "evaluator/evaluate.py")
    baseline_report = grader.evaluate(output)
    metrics = json.loads((output / "search_report.json").read_text())
    assert baseline_report["valid"] and baseline_report["squared_error"] == metrics["squared_error"]
    write_json(output / "grade_report.json", baseline_report)
    local = subprocess.run([sys.executable, "-I", str(ROOT / "participant/check.py"), str(output)],
                           check=True, capture_output=True, text=True, timeout=20)
    assert json.loads(local.stdout)["squared_error"] == baseline_report["squared_error"]
    refusal = subprocess.run([sys.executable, "-B", str(HIDDEN / "freeze_target.py")], capture_output=True, timeout=20)
    assert refusal.returncode != 0
    for filename in (ROOT / "participant/input/target.json", HIDDEN / "target.json"):
        assert hashlib.sha256(filename.read_bytes()).hexdigest() == manifest["target_sha256"]
    assert hashlib.sha256((ROOT / "evaluator/validator.py").read_bytes()).hexdigest() == manifest["validator_sha256"]
    for name, digest in active_hashes.items():
        assert hashlib.sha256((active_root / name).read_bytes()).hexdigest() == digest
    planted = json.loads((HIDDEN / "planted/design.json").read_text())["a"]
    for public_file in (ROOT / "participant").rglob("*.json"):
        content = json.loads(public_file.read_text())
        if isinstance(content, dict) and "a" in content:
            assert content["a"] != planted
    status = {"concept": "concept_3", "generation": 2, "mode": "C_WITNESS_DESIGN",
              "status": "baseline_solved_staged" if baseline_report["passed"] else "staged_ready_pending_champion_audit",
              "ready_for_install": True, "installed": False, "private_staging_only": True,
              "current_generation_unchanged": True, "active_attempt_outputs_read": False,
              "fresh_agents_launched": 0, "champion_method_tested": False, "hardness_verified": False,
              "target": {"direction_count": 8192, "pair_count": 4096,
                         "counts": {"0": 3328, "1": 512, "2": 256}, "energy_integer_sum": 1024,
                         "max_submission_bytes": 131072, "attempt_time_limit_seconds": 3600,
                         "target_sha256": manifest["target_sha256"], "frozen_at_utc": manifest["frozen_at_utc"],
                         "solver_based_target_selection": False},
              "planted": audit["planted_report"], "baseline": baseline_report,
              "baseline_search": {key: value for key, value in metrics.items() if key != "restart_records"},
              "audit": {"passed": audit["passed"], "named_checks": audit["named_checks"],
                        "single_lag_score_checks": audit["single_lag_score_checks"],
                        "all_lags_crosschecked": 4096, "directed_bins_crosschecked": 8192,
                        "angular_bins_crosschecked": 4097, "expensive_per_lag_recomputations": 0,
                        "runtime_seconds": audit["runtime_seconds"], "independent_agent_review": False},
              "active_file_hashes_preserved": active_hashes,
              "concerns": ["No champion or RRR run here; main owns the private scale sweep and installation decision.",
                           "A failing bounded local search is not proof of one-hour hardness.",
                           "Audit uses independent arithmetic, not a separate agent review.",
                           "Do not expose staging or hidden files to currently active or future participant agents."],
              "authoring_test_runtime_seconds": time.perf_counter() - started,
              "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    write_json(ROOT / "status.json", status)
    print(json.dumps({"stage": "private_staging_ready", "target_sha256": manifest["target_sha256"],
                      "planted_core_score": audit["planted_report"]["core_score"],
                      "planted_runtime_seconds": audit["planted_report"]["runtime_seconds"],
                      "baseline_core_score": baseline_report["core_score"],
                      "baseline_matched_lags": baseline_report["matched_lags"],
                      "baseline_squared_error": baseline_report["squared_error"],
                      "baseline_search_seconds": metrics["search_runtime_seconds"],
                      "baseline_checker_seconds": baseline_report["runtime_seconds"],
                      "authoring_test_runtime_seconds": status["authoring_test_runtime_seconds"],
                      "active_files_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
