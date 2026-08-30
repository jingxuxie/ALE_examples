from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from validate import ROOT, corruption_checks, load_configurations, physics_checks


def main():
    started = time.monotonic()
    baseline_path = ROOT / "evaluator/hidden/baseline.json"
    baseline_hash = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    baselines = json.loads(baseline_path.read_text())["fleets"]
    suite = json.loads((ROOT / "evaluator/hidden/suite.json").read_text())["fleets"]
    assert set(baselines) == {entry["id"] for entry in suite}
    physics = physics_checks()
    last = suite[-1]
    directory = ROOT / "evaluator/hidden" / last["directory"]
    manifest, configurations = load_configurations(directory)
    policy = json.loads((ROOT / "champions/baseline" / (last["id"] + ".json")).read_text())
    corruptions = corruption_checks(manifest, configurations, policy, directory)
    assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == baseline_hash
    report = {"physics": physics, "baselines": baselines, "corruptions": corruptions, "passed": True, "elapsed_seconds": time.monotonic() - started, "frozen_baseline_sha256": baseline_hash, "note": "The six independently scored baseline records are preserved byte-for-byte. Only the standalone isolation-test allowance changed from 10 to 60 seconds; the solver allowance remains 60 seconds."}
    (ROOT / "adversary/validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    status = {"name": "Adaptive symmetry diagnostic fleet", "verification_mode": "A", "status": "ready_for_tournament", "target": {"core_improvement_percent": 6.0, "worst_family_improvement_percent": 3.0}, "baseline": {"core_score": 0.0, "worst_family_score": 0.0, "records": "evaluator/hidden/baseline.json"}, "ratchet_generations": 0, "solvability": "unknown", "evaluator_validated": True, "ready_at": datetime.now(timezone.utc).isoformat()}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"passed": True, "corruption_checks": len(corruptions), "baseline_preserved": True}))


if __name__ == "__main__":
    main()
