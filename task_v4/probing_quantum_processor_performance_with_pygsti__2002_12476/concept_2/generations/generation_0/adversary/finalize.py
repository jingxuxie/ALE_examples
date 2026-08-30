import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def add_file(path, data):
    content = json.dumps(data, indent=2, allow_nan=False) + "\n"
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "\n".join("+" + line for line in content.splitlines()) + "\n*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True)


def main():
    specification = importlib.util.spec_from_file_location("trusted_evaluator", ROOT / "evaluator/evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    evaluator.integrity_check()
    audit = json.loads((ROOT / "adversary/audit_results.json").read_text())
    assert audit["passed"]
    baseline = evaluator.evaluate(ROOT / "adversary/baseline_witness.json")
    assert baseline["valid"] and baseline["calibration_accepted"] and not baseline["passed"]
    private = evaluator.evaluate(ROOT / "adversary/private_best_witness.json")
    assert private["valid"] and private["calibration_accepted"]
    add_file(ROOT / "adversary/private_best_evaluation.json", private)
    hashes = {}
    for location in [ROOT / "participant", ROOT / "evaluator"]:
        for path in sorted(location.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()
    freeze = {"frozen_at_utc": timestamp, "before_any_fresh_agent_attempt": True,
              "verification_mode": "B", "primary_objective": evaluator.SPEC,
              "file_sha256": hashes, "evaluator_independent_of_participant": True,
              "tested_simulator_maximum_disagreement": audit["maximum_simulator_disagreement"],
              "threshold_policy": "Do not change these thresholds after observing a fresh attempt; use a new ratchet generation instead."}
    add_file(ROOT / "adversary/freeze.json", freeze)
    simplify = lambda result: {key: result[key] for key in ["core_score", "worst_family_score", "runtime_seconds", "passed", "valid", "calibration_accepted"]}
    search_path = ROOT / "adversary/robust_search_results.json"
    search = json.loads(search_path.read_text())
    status = {"concept": "concept_2", "title": "Robust coherent-leakage counterexample to compressed model acceptance",
              "verification_mode": "B_COUNTEREXAMPLE_FALSIFICATION", "status": "ready_for_fresh_attempt",
              "empirical_hardness": "pending_fresh_agent", "frozen_at_utc": timestamp,
              "frozen": True, "known_passing_solution": private["passed"],
              "solvability": "demonstrated" if private["passed"] else "unknown",
              "classification_if_fresh_agent_fails": "hard_verified_achievable" if private["passed"] else "hard_open_candidate",
              "baseline": simplify(baseline), "private_best": simplify(private),
              "fresh_attempts": [], "fresh_agent_calls_by_this_worker": 0, "ratchet_generations": 0,
              "checker_audit": {"passed": audit["passed"], "path": "adversary/audit_results.json"},
              "search_summary": {"initial_random_processors": 12,
                                 "nominal_joint_search_records": sum(len(json.loads((ROOT / "adversary" / name).read_text()))
                                                                     for name in ["joint_results.json", "joint_scaled_results.json"]),
                                 "robust_search_completed_iterations": len(search),
                                 "robust_search_seconds": search[-1]["runtime_seconds"],
                                 "result": "passing witness" if private["passed"] else "no passing witness; best accepted candidate below fixed target"},
              "task_interface": "Static witness.json with version, a 3x5 gate_parameters array, and one 64-character circuit string",
              "evaluator_command": "python evaluator/evaluate.py --submission PATH --output PATH",
              "baseline_command": "python participant/baseline/search.py --output PATH",
              "resources": {"agent_wall_seconds": 3600, "cpu_cores": 4, "address_space_bytes_per_process": 4294967296},
              "required_capability": "Joint constrained search over stationary leakage Hamiltonians and pulse words, preserving compressed model-fit and robustness constraints while returning leakage population yet retaining a predictive discrepancy",
              "handoff": "Main session must run isolated ultima-alpha on participant/ plus empty writable output. This worker ran no fresh agent and makes no empirical-hardness claim."}
    add_file(ROOT / "status.json", status)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
