import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hidden.model import Episode
from hidden.transport import aggregate, launch_command, run_episode, snapshot_submission, tree_hash


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = Path(__file__).resolve().parent / "hidden"


def verify_integrity():
    manifest = json.loads((HIDDEN / "manifest.json").read_text())
    for relative, expected in manifest["files"].items():
        path = ROOT / relative
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("trusted_asset_integrity_failure: " + relative)
    return hashlib.sha256((HIDDEN / "manifest.json").read_bytes()).hexdigest()


def evaluate(submission, policy, isolation="bwrap"):
    started = time.monotonic()
    report = {"valid": False, "passed": False, "accuracy_passed": False, "core_score": 0.0,
              "average_family_score": 0.0, "worst_family_score": 0.0,
              "runtime_resource_score": 0.0, "reason": "not_started", "isolation": isolation}
    try:
        manifest_hash = verify_integrity()
        benchmark = json.loads((HIDDEN / "benchmark.json").read_text())
        runs = HIDDEN / "runs"
        runs.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="evaluation-", dir=runs) as temporary:
            temporary = Path(temporary)
            snapshot = temporary / "submission"
            submission_hash = snapshot_submission(submission, snapshot, policy)
            command = launch_command(snapshot, policy, isolation)
            records = []
            for case_index, specification in enumerate(benchmark["episodes"]):
                episode = Episode(int(specification["seed_hex"], 16), specification["family"], specification["shape"])
                fingerprint = hashlib.sha256(json.dumps(episode.targets, separators=(",", ":")).encode()).hexdigest()
                if fingerprint != specification["targets_sha256"]:
                    raise ValueError("fixed_target_reproduction_failure")
                record = run_episode(episode, command, snapshot, temporary / (str(case_index) + ".stderr"))
                record.update(episode_id=specification["id"], family=specification["family"], qubits=episode.grid.qubits)
                records.append(record)
            if tree_hash(snapshot) != submission_hash:
                raise ValueError("submission_snapshot_modified")
            if verify_integrity() != manifest_hash:
                raise ValueError("parent_integrity_audit_failed")
            report = aggregate(records, isolated=isolation == "bwrap")
            report.update(isolation=isolation, submission_sha256=submission_hash,
                          manifest_sha256=manifest_hash, benchmark_id=benchmark["benchmark_id"])
    except (OSError, ValueError, TypeError, KeyError) as exception:
        report.update(valid=False, passed=False, reason=str(exception)[:300])
    report["evaluator_wall_seconds"] = time.monotonic() - started
    return report


def main():
    parser = argparse.ArgumentParser(description="Trusted active-MRB evaluator; never imports submission code.")
    parser.add_argument("--submission")
    parser.add_argument("--policy", default="policy.py")
    parser.add_argument("--report")
    parser.add_argument("--isolation", choices=("bwrap", "audit"), default="bwrap")
    parser.add_argument("--allow-unsafe-local", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    arguments = parser.parse_args()
    if arguments.isolation == "audit" and not arguments.allow_unsafe_local:
        parser.error("audit mode requires --allow-unsafe-local and can never pass")
    if arguments.self_check:
        from hidden.selfcheck import self_check
        report = self_check(arguments.isolation)
    else:
        if not arguments.submission:
            parser.error("--submission is required unless --self-check")
        report = evaluate(arguments.submission, arguments.policy, arguments.isolation)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        Path(arguments.report).write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
