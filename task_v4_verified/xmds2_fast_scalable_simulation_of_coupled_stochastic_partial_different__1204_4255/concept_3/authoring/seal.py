import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]


def main():
    evaluation = json.loads((ROOT / "attempts/baseline_evaluation.json").read_text())
    public = json.loads((ROOT / "participant/baseline/score.json").read_text())
    validation = json.loads((ROOT / "adversary/validation.json").read_text())
    cli = json.loads((ROOT / "adversary/cli_validation.json").read_text())
    assert evaluation["valid"] and not evaluation["passed"]
    assert validation["passed"] and cli["passed"]
    assert public["artifact_canonical_sha256"] == evaluation["artifact_canonical_sha256"] == cli["artifact_canonical_sha256"]
    (ROOT / "attempts/baseline_smoke.json").write_text(json.dumps(public, indent=2) + "\n")
    summary = {"status": "baseline_validated_pending_tournament", "fresh_agents_run": 0, "role": "privileged_generation_worker", "baseline_valid": True, "baseline_passed": False, "core_score": evaluation["core_score"], "worst_family_score": evaluation["worst_family_score"], "worst_case_score": evaluation["worst_case_score"], "runtime_score": evaluation["runtime_score"], "resource_score": evaluation["resource_score"], "runtime_seconds": evaluation["runtime_seconds"], "reason": evaluation["reason"]}
    (ROOT / "attempts/status.json").write_text(json.dumps(summary, indent=2) + "\n")
    audit_status = {"status": "parser_cli_and_numerical_audits_passed", "fresh_agents_run": 0, "hardness_finalized": False, "validation": "validation.json", "cli_validation": "cli_validation.json"}
    (ROOT / "adversary/status.json").write_text(json.dumps(audit_status, indent=2) + "\n")
    paths = ["participant/input/protocol.json", "participant/input/SPEC.md", "participant/input/public_cases.json", "participant/baseline/control.json", "participant/baseline/make_control.py", "participant/workspace/field_control.py", "participant/workspace/smoke.py", "evaluator/evaluate.py", "evaluator/hidden/field_control.py", "evaluator/hidden/protocol.json", "evaluator/hidden/cases.json"]
    paths.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / "evaluator/hidden/references").glob("*.npz")))
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    manifest = {"protocol": "coherent_gp_splitter_v1", "date": "2026-08-28", "status": "pending_tournament", "target_fixed_before_baseline_measurement": True, "fresh_agents_run": 0, "hardness_finalized": False, "python": platform.python_version(), "python_executable": sys.executable, "numpy": np.__version__, "scipy": scipy.__version__, "sha256": hashes}
    (ROOT / "freeze_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
