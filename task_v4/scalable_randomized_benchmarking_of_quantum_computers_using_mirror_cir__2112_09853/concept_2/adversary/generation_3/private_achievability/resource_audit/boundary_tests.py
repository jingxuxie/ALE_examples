import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sys


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
sys.path.insert(0, str(AREA))
from runtime.model import Episode
from runtime.transport import launch_command, run_episode
from cgroup_tests import run_probe


runtime_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (AREA / "runtime").glob("*.py")}
records = []
for mode in ("cgroup_tamper", "orphan_burn", "threads"):
    directory = AREA / "cgroup_runs" / mode
    directory.mkdir(exist_ok=False)
    artifact = directory / "submission"
    artifact.mkdir()
    shutil.copyfile(AREA / "boundary_policy.py", artifact / "policy.py")
    (artifact / "settings.json").write_text(json.dumps({"mode": mode}) + "\n")
    seed = secrets.randbits(128)
    record = run_episode(Episode(seed, "distant_pairs", (4, 4)),
                         launch_command(artifact, "policy.py", "bwrap"), artifact,
                         directory / "stderr.txt", isolation="bwrap")
    record.update(mode=mode, seed_hex=format(seed, "032x"),
                  probe_details=(directory / "stderr.txt").read_text(),
                  policy_sha256=hashlib.sha256((artifact / "policy.py").read_bytes()).hexdigest())
    (directory / "report.json").write_text(json.dumps(record, indent=2) + "\n")
    assert record["valid"], record
    assert record["cpu_accounting"]["owned_episode_cgroup_removed"], record
    if mode == "orphan_burn":
        assert record["cpu_seconds"] >= 1.5
    if mode == "threads":
        assert record["cpu_seconds"] >= 1.
    records.append(record)
    print(json.dumps(dict(mode=mode, cpu_seconds=record["cpu_seconds"], valid=record["valid"])), flush=True)
compatibility_overlimit = run_probe("compatibility_auto_reap_over_limit", "auto_reap", 31.)
assert not compatibility_overlimit["record"]["valid"]
assert compatibility_overlimit["record"]["reason"] == "aggregate_cpu_limit"
assert compatibility_overlimit["record"]["cpu_seconds"] >= 62.
assert runtime_hashes == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (AREA / "runtime").glob("*.py")}
report = dict(passed=True, tests=records, compatibility_auto_reap_overlimit=compatibility_overlimit,
              private_runtime_sha256=runtime_hashes,
              frozen_manifest_sha256=hashlib.sha256((ROOT / "evaluator/hidden/manifest.json").read_bytes()).hexdigest())
(AREA / "cgroup_boundary_report.json").write_text(json.dumps(report, indent=2) + "\n")
