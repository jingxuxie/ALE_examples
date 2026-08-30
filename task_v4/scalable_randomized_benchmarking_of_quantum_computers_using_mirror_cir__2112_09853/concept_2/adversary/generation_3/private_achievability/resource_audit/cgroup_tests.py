import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys


os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
sys.path.insert(0, str(AREA))
from runtime.model import Episode
from runtime.selfcheck import self_check
from runtime.transport import aggregate, launch_command, run_episode, snapshot_submission


def run_probe(label, mode, seconds=1., isolation="bwrap"):
    directory = AREA / "cgroup_runs" / label
    if (directory / "report.json").exists():
        cached = json.loads((directory / "report.json").read_text())
        assert cached["mode"] == mode and cached["seconds_per_worker"] == seconds
        print(json.dumps(dict(label=label, reused_completed_private_result=True)), flush=True)
        return cached
    directory.mkdir(parents=True, exist_ok=False)
    artifact = directory / "submission"
    artifact.mkdir()
    shutil.copyfile(AREA / "policy.py", artifact / "policy.py")
    if mode == "no_cldwait":
        shutil.copyfile(AREA / "signal_flags.so", artifact / "signal_flags.so")
    (artifact / "settings.json").write_text(json.dumps(dict(mode=mode, seconds=seconds, workers=2)) + "\n")
    seed = secrets.randbits(128)
    episode = Episode(seed, "distant_pairs", (4, 4))
    record = run_episode(episode, launch_command(artifact, "policy.py", isolation), artifact, directory / "stderr.txt", isolation=isolation)
    (directory / "transport_record.json").write_text(json.dumps(record, indent=2) + "\n")
    messages = []
    decoder = json.JSONDecoder()
    for line in (directory / "stderr.txt").read_text().splitlines():
        remaining = line.lstrip()
        while remaining.startswith("{"):
            value, consumed = decoder.raw_decode(remaining)
            messages.append(value)
            remaining = remaining[consumed:].lstrip()
    result = dict(label=label, mode=mode, seconds_per_worker=seconds, isolation=isolation,
                  seed_hex=format(seed, "032x"), record=record, trusted_probe_messages=messages,
                  policy_sha256=hashlib.sha256((artifact / "policy.py").read_bytes()).hexdigest(),
                  probe_self_cpu_sum=sum(message.get("self_cpu_seconds", 0.) for message in messages))
    (directory / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(label=label, valid=record["valid"], reason=record["reason"],
                         cpu_seconds=record["cpu_seconds"], launcher_cpu=record["launcher_rusage_cpu_seconds"],
                         probe_cpu=result["probe_self_cpu_sum"], wall_seconds=record["wall_seconds"])), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("resources", "selfcheck", "baseline"), required=True)
    parser.add_argument("--run-id", default="")
    arguments = parser.parse_args()
    assert all(character.isalnum() or character in "_-" for character in arguments.run_id)
    suffix = "_" + arguments.run_id if arguments.run_id else ""
    runtime_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (AREA / "runtime").glob("*.py")}
    manifest_path = ROOT / "evaluator/hidden/manifest.json"
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert manifest_hash == "35ede7981b1fbe3beb7aff3e09fa4c0cd5ea4de05a293814b7823d2d1175fd72"
    started = datetime.now(timezone.utc).isoformat()
    if arguments.suite == "resources":
        results = []
        for label, mode, seconds in (("ordinary_child", "fork", 1.), ("single", "single", 1.),
                                     ("exec", "exec", 1.), ("orphan", "orphan", 1.),
                                     ("auto_reap_small", "auto_reap", 1.),
                                     ("auto_reap_over_limit", "auto_reap", 31.),
                                     ("no_cldwait_over_limit", "no_cldwait", 31.),
                                     ("ordinary_over_limit", "fork", 31.),
                                     ("no_cldwait_small_retry", "no_cldwait", 1.)):
            result = run_probe(arguments.run_id + "_" + label if arguments.run_id else label, mode, seconds)
            results.append(result)
            expected_rejection = seconds == 31.
            assert result["record"]["valid"] != expected_rejection, result
            if expected_rejection:
                assert result["record"]["reason"] == "aggregate_cpu_limit", result
                assert result["record"]["cpu_seconds"] >= 62., result
            elif mode != "orphan":
                assert result["record"]["cpu_seconds"] >= result["probe_self_cpu_sum"] - .05, result
            assert result["record"]["cpu_accounting"]["owned_episode_cgroup_removed"], result
        report = dict(passed=True, tests=results)
    elif arguments.suite == "selfcheck":
        report = self_check("bwrap")
    else:
        directory = AREA / ("baseline_validation" + suffix)
        directory.mkdir(exist_ok=False)
        artifact = directory / "submission"
        snapshot_submission(ROOT / "participant/baseline", artifact, "policy.py")
        benchmark = json.loads((ROOT / "evaluator/hidden/benchmark.json").read_text())
        records = []
        for index, case in enumerate(benchmark["episodes"]):
            episode = Episode(int(case["seed_hex"], 16), case["family"], case["shape"])
            record = run_episode(episode, launch_command(artifact, "policy.py", "bwrap"), artifact,
                                 directory / (str(index) + ".stderr"))
            record.update(family=case["family"], shape=case["shape"], case_index=index)
            records.append(record)
            print(json.dumps(dict(case_index=index, valid=record["valid"], cpu_seconds=record["cpu_seconds"])), flush=True)
        report = aggregate(records, isolated=True)
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == manifest_hash
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest["files"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    report.update(private_prototype=True, started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
                  frozen_manifest_sha256=manifest_hash, frozen_manifest_files_unchanged=True,
                  private_runtime_sha256=runtime_hashes)
    assert runtime_hashes == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (AREA / "runtime").glob("*.py")}
    destination = AREA / ("cgroup_" + arguments.suite + suffix + "_report.json")
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(report=str(destination), passed=report.get("passed"), valid=report.get("valid"),
                         average=report.get("average_family_score"), worst=report.get("worst_family_score"))), flush=True)


if __name__ == "__main__":
    main()
