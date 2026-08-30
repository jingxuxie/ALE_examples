import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import secrets
import shutil
import sys
import time


AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
sys.path.insert(0, str(ROOT / "participant/workspace"))
import model
from transport import launch_command, run_episode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--mode", choices=("single", "fork", "auto_reap", "no_cldwait", "orphan", "exec", "tamper"), default="single")
    parser.add_argument("--seconds", type=float, default=1.)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--isolation", choices=("audit", "bwrap"), default="bwrap")
    parser.add_argument("--as-pid-1", action="store_true")
    parser.add_argument("--subreaper", action="store_true")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--guardian", action="store_true")
    arguments = parser.parse_args()
    assert 0 < arguments.seconds <= 32
    assert 1 <= arguments.workers <= 2
    assert not arguments.as_pid_1 or arguments.isolation == "bwrap"
    directory = AREA / "runs" / arguments.label
    directory.mkdir(parents=True, exist_ok=False)
    artifact = directory / "submission"
    artifact.mkdir()
    shutil.copyfile(AREA / "policy.py", artifact / "policy.py")
    if arguments.mode == "no_cldwait":
        shutil.copyfile(AREA / "signal_flags.so", artifact / "signal_flags.so")
    (artifact / "settings.json").write_text(json.dumps(vars(arguments), indent=2) + "\n")
    if arguments.subreaper:
        library = ctypes.CDLL(None, use_errno=True)
        if library.prctl(36, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER")
    command = launch_command(artifact, "policy.py", arguments.isolation)
    if arguments.guardian:
        assert arguments.isolation == "bwrap" and not arguments.as_pid_1
        command = [sys.executable, "-I", "-S", "-B", str(AREA / "guardian_launcher.py"),
                   "--artifact", str(artifact), "--audit-path", str(directory / "guardian_audit.json")]
    if arguments.as_pid_1:
        command.insert(1, "--as-pid-1")
    if arguments.trace:
        command = ["/usr/bin/strace", "-f", "-qq", "-tt", "-e", "trace=process,read,write,eventfd2", "-o", str(directory / "trace.txt")] + command
    seed = secrets.randbits(128)
    episode = model.Episode(seed, "distant_pairs", (4, 4))
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    record = run_episode(episode, command, artifact, directory / "stderr.txt")
    adopted = []
    if arguments.subreaper:
        deadline = time.monotonic() + 5
        while True:
            try:
                child_pid, status, usage = os.wait4(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if child_pid:
                adopted.append(dict(pid=child_pid, status=status, cpu_seconds=usage.ru_utime + usage.ru_stime))
            elif time.monotonic() >= deadline:
                raise RuntimeError("subreaper_drain_timeout")
            else:
                time.sleep(.01)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    messages = [json.loads(line) for line in (directory / "stderr.txt").read_text().splitlines()
                if line.startswith("{")]
    observed_cpu = sum(message.get("self_cpu_seconds", 0.) for message in messages)
    report = dict(completed_utc=datetime.now(timezone.utc).isoformat(), settings=vars(arguments),
                  seed_hex=format(seed, "032x"), command=command, frozen_transport_record=record,
                  trusted_probe_messages=messages, probe_self_cpu_sum=observed_cpu,
                  parent_cpu_after_optional_drain=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                  adopted_children=adopted, policy_sha256=hashlib.sha256((artifact / "policy.py").read_bytes()).hexdigest(),
                  frozen_manifest_sha256=hashlib.sha256((ROOT / "evaluator/hidden/manifest.json").read_bytes()).hexdigest())
    if arguments.guardian:
        report["guardian_audit"] = json.loads((directory / "guardian_audit.json").read_text())
        report["guardian_would_reject_aggregate"] = report["guardian_audit"]["cpu_seconds"] > 60.25
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
