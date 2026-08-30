import json
from pathlib import Path
import subprocess
import sys
import tempfile

from model import Episode
from transport import aggregate, launch_command, run_episode, snapshot_submission


assert not Path("/sys/fs/cgroup").exists()
assert not Path("/run/user/2020/bus").exists()
with tempfile.TemporaryDirectory(prefix="audit-compatibility-") as temporary:
    directory = Path(temporary)
    artifact = directory / "submission"
    snapshot_submission("/baseline", artifact, "policy.py")
    audit_record = run_episode(Episode(112358, "local_clusters", (4, 4)),
                               launch_command(artifact, "policy.py", "audit"), artifact,
                               directory / "audit.stderr", isolation="audit")
    assert audit_record["valid"], audit_record
    assert audit_record["cpu_accounting"]["source"] == "unsafe_audit_RUSAGE_CHILDREN_inexact"
    perfect = dict(audit_record, family="local_clusters", normalized_mse=0.)
    perfect_audit = aggregate([perfect], isolated=True)
    assert perfect_audit["accuracy_passed"] and not perfect_audit["passed"]
    strict_record = run_episode(Episode(112359, "local_clusters", (4, 4)),
                                launch_command(artifact, "policy.py", "bwrap"), artifact,
                                directory / "strict.stderr", isolation="bwrap")
    assert not strict_record["valid"] and strict_record["cpu_accounting"] is None
    command = [sys.executable, "-B", "/submission/develop.py", "--submission", "/baseline",
               "--policy", "policy.py", "--isolation", "audit", "--family", "local_clusters", "--shape", "4x4"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    development = json.loads(result.stdout)
    assert development["valid"] and not development["passed"]
    print(json.dumps(dict(passed=True, no_cgroup_fs_or_bus=True, top_level_import_succeeded=True,
                          audit_record=audit_record, perfect_audit_never_certified=not perfect_audit["passed"],
                          official_missing_counter_fails_closed=strict_record,
                          public_develop_cli_valid=development["valid"],
                          public_develop_cli_passed=development["passed"]), indent=2))
