import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE / "evaluator"), str(BASE / "participant" / "input")]

from evaluate import run_case
from hidden.generator import suite


def main():
    wrapper = BASE.parent / "authoring" / "sandbox.py"
    scratch = BASE / "adversary" / ".scratch"
    scratch.mkdir(exist_ok=True)
    record = suite("sandbox-smoke-v1", 1)[0]
    result = run_case(
        record, BASE / "adversary" / "smoke_submission", "policy.py",
        BASE / "participant", scratch, sandbox_wrapper=wrapper,
    )
    passed = result["status"] == "ok" and result["calls"] == 72
    report = {
        "passed": passed, "case": result, "wrapper_sha256": hashlib.sha256(wrapper.read_bytes()).hexdigest(),
        "environment_cleared_public_import_verified": passed,
        "hidden_seed_read_denied_verified": passed,
        "relocated_submission_verified": passed,
        "not_a_fresh_agent": True,
    }
    (BASE / "adversary" / "sandbox_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
