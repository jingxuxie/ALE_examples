from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1] / "concept_3"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    log = (ROOT / "adversary/validation.log").read_text()
    smoke = json.loads((ROOT / "adversary/public_allowlist_smoke.json").read_text())
    baseline = json.loads((ROOT / "adversary/baseline_hidden.json").read_text())
    assert "Ran 12 tests" in log and log.rstrip().endswith("OK")
    assert smoke["passed"]
    assert baseline["complete_hidden_suite"] and not baseline["protocol_failures"]
    sys.path.insert(0, str(ROOT / "evaluator"))
    from evaluate import hidden_cases
    dev = json.loads((ROOT / "participant/input/dev_cases.json").read_text())
    hidden = hidden_cases()
    assert not {case["seed"] for case in dev}.intersection(case["seed"] for case in hidden)
    for directory in ("attempts", "champions", "adversary"):
        (ROOT / directory).mkdir(exist_ok=True)
    champion = ROOT / "champions/baseline"
    champion.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "participant/baseline/policy.py", champion / "policy.py")
    shutil.copy2(ROOT / "adversary/baseline_hidden.json", champion / "score.json")
    validation = {"passed": True, "tests": 12, "model_invariants": "independent exhaustive graph degree/common-neighbor/K4 checks and parity replay", "protocol_checks": "budgets, malformed messages, oversized lines, missing artifacts, receive and blocked-send deadlines", "isolation_probe_passed": True, "public_allowlist_smoke_passed": True, "baseline_protocol_failures": 0, "disjoint_public_private_seeds": True, "sandbox_timing": "trusted startup handshake excludes OS initialization and cleanup from policy interaction time; CPU/address-space limits remain enforced"}
    write_json(ROOT / "adversary/validation.json", validation)
    hashes = {}
    for directory in (ROOT / "participant", ROOT / "evaluator"):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.name != "frozen.json":
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()
    write_json(ROOT / "evaluator/frozen.json", {"frozen_at_utc": timestamp, "sha256": hashes, "target_frozen_before_fresh": True})
    status = {"concept": "Parity-invisible residual mechanism diagnosis", "verification_mode": "E", "status": "built", "frozen": True, "frozen_at_utc": timestamp, "target": {"correct": 171, "episodes": 180, "minimum_correct_per_cell": 18, "episodes_per_cell": 20, "query_budget": 480}, "baseline_core_score": baseline["core_score"], "baseline_worst_family_score": baseline["worst_family_score"], "baseline_correct": baseline["correct"], "known_passing_solution": False, "solvability": "unknown", "ratchet_generations": 0, "fresh_attempts": []}
    write_json(ROOT / "status.json", status)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
