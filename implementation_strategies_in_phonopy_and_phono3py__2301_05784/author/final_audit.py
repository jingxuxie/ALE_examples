"""Finalize a negative result only after verifying immutable pilot evidence."""

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from run_pilots import tree_digest


ROOT = Path(__file__).resolve().parent.parent
pilots = {}
for name in ("fitting", "cubic", "grid", "polar"):
    evidence_path = ROOT / "author/pilot_logs" / f"{name}_pilot.json"
    evidence = json.loads(evidence_path.read_text())
    score_name = "fitting_pilot_corrected.json" if name == "fitting" else f"{name}_pilot.json"
    score_path = ROOT / "author/scores" / score_name
    report = json.loads(score_path.read_text())
    assert evidence["model"] == "ultima-alpha"
    assert evidence["returncode"] == 0 and evidence["has_solution"]
    assert evidence["elapsed_seconds"] < 3600
    assert evidence["participant_sha256_before"] == evidence["participant_sha256_after"]
    assert tree_digest(ROOT / "concepts" / name / "participant") == evidence["participant_sha256_before"]
    assert tree_digest(ROOT / "concepts" / name / "attempt") == evidence["attempt_sha256"]
    assert report["summary"]["completed_cases"] == report["summary"]["total_cases"]
    assert report["summary"]["mean_core"] > 0.90
    assert report["summary"]["worst_family"] > 0.90
    pilots[name] = {"model": evidence["model"], "model_seconds": evidence["elapsed_seconds"],
                    "summary": report["summary"],
                    "score_report": str(score_path.relative_to(ROOT)),
                    "evidence": str(evidence_path.relative_to(ROOT)),
                    "participant_unchanged": True, "attempt_unchanged": True}
for path in (ROOT / "author").glob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
runner = ROOT.parents[1] / "run_allowlisted_codex.sh"
runner_hash = hashlib.sha256(runner.read_bytes()).hexdigest()
assert all(json.loads((ROOT / pilots[name]["evidence"]).read_text())["runner_sha256"] == runner_hash for name in pilots)
assert not any((ROOT / "concepts").glob("*/ratchet*/participant"))
grid_search = json.loads((ROOT / "concepts/grid/private/reference/bounded_search_01/summary.json").read_text())
assert grid_search["mean_core"] > 0.90 and grid_search["originals_unchanged"]
status = {
    "status": "rejected", "accepted_task": None,
    "reason": "All four valid initial fresh-agent submissions are solved (>0.90 mean and worst-family); expanded source-grounded fitting/grid searches reveal no genuine failure region. No artificial ratchet is justified.",
    "completed_utc": datetime.now(timezone.utc).isoformat(),
    "pilots_built": 4, "valid_fresh_attempts": 4, "pilot_limit_seconds": 3600,
    "counterexample_search_concepts": ["fitting", "grid"],
    "ratchets_built": 0, "fresh_ratchet_confirmation_attempts": 0,
    "confirmation_not_run_reason": "No concept survived the source-grounded counterexample gate; phase7 is inapplicable.",
    "initial_stdin_startup_launches": "unscored; preserved in author/pilot_logs_stdin_blocked",
    "reference_correction": "author/SI_ORACLE_CORRECTION.md",
    "scoring_audit": "author/CONTRACT_AUDIT.md", "report": "REPORT.md",
    "runner_unchanged": True, "runner_sha256": runner_hash, "pilots": pilots,
    "fitting_expanded_report": "concepts/fitting/private/reference/counterexamples/REPORT.md",
    "grid_expanded_report": "concepts/grid/private/reference/bounded_search_01/README.md",
}
(ROOT / "STATUS.json").write_text(json.dumps(status, indent=2, allow_nan=False) + "\n")
(ROOT / "author/final_validation.json").write_text(json.dumps({
    "passed": True, "checks": ["four completed requested-model attempts", "one-hour limits",
    "public and submission tree hashes unchanged", "all valid cases completed", "all mean/worst-family scores solved",
    "runner unchanged", "author-script syntax", "no unjustified ratchet directories", "expanded grid search passed"],
    "completed_utc": status["completed_utc"], "known_prototype_defects": ["archived original Si oracle", "documented baseline-calibration shortcuts"],
}, indent=2) + "\n")
print(json.dumps({"status": status["status"], "pilots": {name: value["summary"]["mean_core"] for name, value in pilots.items()}, "validation": "passed"}, indent=2))
