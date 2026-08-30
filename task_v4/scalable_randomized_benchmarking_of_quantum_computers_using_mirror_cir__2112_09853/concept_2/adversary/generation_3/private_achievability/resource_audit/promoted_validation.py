import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(AREA))

import evaluate
from hidden.model import Episode
from hidden.transport import launch_command, run_episode
import cgroup_tests


def source_hashes():
    names = ("evaluator/evaluate.py", "evaluator/hidden/transport.py",
             "evaluator/hidden/cgroup_accounting.py", "evaluator/hidden/model.py",
             "evaluator/hidden/selfcheck.py", "evaluator/hidden/manifest.json",
             "participant/workspace/transport.py", "participant/workspace/cgroup_accounting.py",
             "participant/workspace/model.py", "participant/workspace/develop.py",
             "participant/baseline/policy.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def resources(run_id):
    cgroup_tests.Episode = Episode
    cgroup_tests.launch_command = launch_command
    cgroup_tests.run_episode = run_episode
    records = []
    cases = (("ordinary_child", "fork", 1.), ("single", "single", 1.),
             ("exec", "exec", 1.), ("orphan", "orphan", 1.),
             ("auto_reap_small", "auto_reap", 1.), ("no_cldwait_small", "no_cldwait", 1.),
             ("ordinary_over_limit", "fork", 31.), ("auto_reap_over_limit", "auto_reap", 31.),
             ("no_cldwait_over_limit", "no_cldwait", 31.))
    for label, mode, seconds in cases:
        result = cgroup_tests.run_probe(run_id + "_" + label, mode, seconds)
        record = result["record"]
        expected_rejection = seconds == 31.
        assert record["valid"] != expected_rejection, result
        if expected_rejection:
            assert record["reason"] == "aggregate_cpu_limit", result
            assert record["cpu_seconds"] >= 62., result
        elif mode != "orphan":
            assert record["cpu_seconds"] >= result["probe_self_cpu_sum"] - .05, result
        assert record["cpu_accounting"]["owned_episode_cgroup_removed"], result
        records.append(result)
    return {"passed": True, "resource_checks_passed": len(records), "tests": records}


def audit_compatibility():
    command = launch_command(ROOT / "participant/workspace", "develop.py", "bwrap")
    separator = command.index("--")
    command = command[:separator] + [
        "--ro-bind", str(ROOT / "participant/baseline"), "/baseline",
        "--ro-bind", str(AREA / "runtime/audit_inside.py"), "/audit-check.py",
        "--", sys.executable, "-E", "-s", "-B", "-c",
        "import runpy,sys;sys.path.insert(0,'/submission');runpy.run_path('/audit-check.py',run_name='__main__')"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    (AREA / "promoted_public_audit_compatibility_stderr.txt").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["passed"], report
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("resources", "audit"), required=True)
    parser.add_argument("--run-id", default="promoted_" + uuid.uuid4().hex)
    arguments = parser.parse_args()
    assert all(character.isalnum() or character in "_-" for character in arguments.run_id)
    hashes_before = source_hashes()
    manifest_hash = evaluate.verify_integrity()
    started = datetime.now(timezone.utc).isoformat()
    if arguments.suite == "resources":
        assert evaluate.kernel_accounting_parent_available()
        report = resources(arguments.run_id)
    else:
        report = audit_compatibility()
    assert source_hashes() == hashes_before
    assert evaluate.verify_integrity() == manifest_hash
    report.update(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
                  promoted_code_sha256=hashes_before, manifest_sha256=manifest_hash,
                  run_id=arguments.run_id, test_harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    destination = AREA / ("promoted_" + arguments.suite + "_report.json")
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(destination), "passed": report["passed"]}), flush=True)


if __name__ == "__main__":
    main()
