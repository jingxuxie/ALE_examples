import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import evaluate


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    public = ROOT / "participant" / "input"
    private = ROOT / "evaluator" / "hidden"
    audits = json.loads((ROOT / "adversary" / "audit_results.json").read_text())
    assert audits["all_checks_passed"]
    protocol = json.loads((public / "protocol.json").read_text())
    assert protocol["core_rmse_max"] == 0.020
    assert set(protocol["family_rmse_max"].values()) == {0.025}
    assert protocol["device_family_rmse_max"] == 0.040
    write(private / "protocol.json", protocol)
    write(private / "integrity.json", {name: digest(private / name) for name in ["truth.npz", "protocol.json"]})
    old_manifest = json.loads((public / "manifest.json").read_text())
    for name, expected in old_manifest.items():
        if name.endswith(".npz"):
            assert digest(public / name) == expected
    write(public / "manifest.json", {name: digest(public / name) for name in old_manifest})
    baseline = evaluate(ROOT / "adversary" / "baseline_predictions.json")
    assert baseline["valid"] and not baseline["passed"]
    write(ROOT / "adversary" / "baseline_score.json", baseline)
    dataset_summary = json.loads((ROOT / "adversary" / "dataset_summary.json").read_text())
    for split in ["train", "development"]:
        with np.load(public / (split + ".npz"), allow_pickle=False) as archive:
            dataset_summary[split]["total_shots"] = int(np.sum(archive["shots"]))
    write(ROOT / "adversary" / "dataset_summary.json", dataset_summary)
    status = {
        "concept": "concept_3", "name": "Finite-shot quantum memory extrapolation",
        "verification_mode": "D_HIDDEN_PREDICTION", "package_status": "ready",
        "stage": "ready_for_fresh_attempt", "status": None,
        "hardness_decision": "pending_main_session_fresh_attempt",
        "solvability": "unknown_from_participant_information",
        "known_passing_data_only_solution": False,
        "oracle_validation_is_not_achievability": True,
        "fresh_attempts": [], "ratchet_generations": 0,
        "target_frozen_before_launch": True, "frozen_date": "2026-08-28",
        "thresholds": {"macro_rmse": 0.020, "every_family_rmse": 0.025, "every_device_family_rmse": 0.040},
        "baseline": {key: baseline[key] for key in ["core_score", "worst_family_score", "macro_rmse", "family_rmse", "worst_device_family_rmse", "passed", "valid"]},
        "audit_passed": True, "audit_results": "adversary/audit_results.json",
        "dataset_summary": "adversary/dataset_summary.json",
        "participant_root": "participant",
        "submission_format": "static predictions.json file, keys ids and p1",
        "evaluation_command": "python evaluator/evaluate.py --submission PATH --output PATH",
        "isolation_owner": "main session; allow only participant and an empty writable attempt directory",
        "resource_limits": {"seconds": 3600, "cpu_affinity_size": 8, "address_space_gib_per_process": 8},
        "next_decision": "If a fresh agent fails and no data-only passing solution is known, hard_open_candidate; do not treat the label oracle as achievability."
    }
    diagnostics_path = ROOT / "adversary" / "diagnostics.json"
    if diagnostics_path.exists():
        diagnostics = json.loads(diagnostics_path.read_text())
        status["counterexample_search"] = diagnostics["private_counterexample_search"]
        status["local_information"] = diagnostics.get("local_information")
    write(ROOT / "status.json", status)
    immutable = [path for directory in [ROOT / "participant", ROOT / "evaluator"]
                 for path in directory.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    write(ROOT / "adversary" / "frozen_manifest.json", {str(path.relative_to(ROOT)): digest(path) for path in sorted(immutable)})
    all_files = sorted(str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    if "adversary/files_manifest.json" not in all_files:
        all_files.append("adversary/files_manifest.json")
    write(ROOT / "adversary" / "files_manifest.json", {"root": str(ROOT), "files": sorted(all_files)})
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
