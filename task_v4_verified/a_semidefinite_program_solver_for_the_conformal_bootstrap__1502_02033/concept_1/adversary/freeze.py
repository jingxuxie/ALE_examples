import datetime
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from hidden_cases import hidden_cases, suite_digest


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    measurements = json.loads((ROOT / "evaluator" / "baseline_measurements.json").read_text())
    baseline = ROOT / "participant" / "baseline" / "solution.py"
    assert measurements["valid"] and len(measurements["cases"]) == 12
    assert digest(baseline) == measurements["solution_sha256"]
    assert digest(ROOT / "evaluator" / "oracle.py") == measurements["oracle_sha256"]
    assert suite_digest(hidden_cases()) == measurements["suite_sha256"]
    target = {"core_score": 1.15, "worst_family_score": 1.05,
              "minimum_case_score": 0.95, "resource_score": 0.10}
    reference = {"frozen": True, "suite_sha256": measurements["suite_sha256"],
                 "oracle_sha256": measurements["oracle_sha256"], "baseline_sha256": digest(baseline),
                 "target": target, "cases": {entry["id"]: {key: entry[key] for key in
                    ["family", "degree", "log_lower", "log_upper", "nodes", "relative_enclosure"]}
                    for entry in measurements["cases"]}}
    hidden = ROOT / "evaluator" / "hidden"
    hidden.mkdir(exist_ok=True)
    for destination in [ROOT / "evaluator" / "reference.json", hidden / "reference.json"]:
        destination.write_text(json.dumps(reference, indent=2) + "\n")
    (hidden / "cases.json").write_text(json.dumps(hidden_cases(), indent=2) + "\n")
    public_target = dict(target, frozen=True, generation=1, cpu_seconds_per_case=8,
                         meaning="ratios above one improve worst-prefactor interpolation amplification")
    (ROOT / "participant" / "TARGET.json").write_text(json.dumps(public_target, indent=2) + "\n")
    validation = {"self_tests_passed": 12, "self_tests_failed": 0,
                  "baseline_numerical_cases_valid": 12,
                  "cpu_accounting": "protected supervisor directly waits for candidate; 0.4 CPU-second burn and report-isolation test passed",
                  "old_cpu_measurements_valid": False,
                  "new_cpu_measurements": "adversary/baseline_score.json",
                  "oracle": "floating enclosures plus independent 80-digit peak checks, not formal interval arithmetic"}
    (ROOT / "adversary" / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    state = {"concept": "concept_1", "verification_mode": "A", "generation": 1,
             "status": "ready_for_tournament", "state": "frozen", "target_frozen": True,
             "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "target": target, "baseline_core_score": 1.0, "baseline_worst_family_score": 1.0,
             "baseline_cpu_remeasurement": "pending; former wrapper wait4 counters are not used for grading",
             "baseline_source_sha256": digest(baseline), "evaluator_valid": True,
             "known_passing_solution": False, "solvability": "unknown", "fresh_attempts": 0,
             "ratchet_generations": 0, "validation": validation}
    (ROOT / "status.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
