import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def resource_limits():
    available = sorted(os.sched_getaffinity(0))
    start = (os.getpid() * 7) % len(available)
    os.sched_setaffinity(0, {available[(start + offset) % len(available)] for offset in range(min(4, len(available)))})
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def digest_tree(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int, choices=[1, 2, 3])
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--generation-root")
    arguments = parser.parse_args()
    concept = Path(arguments.generation_root).resolve() if arguments.generation_root else ROOT / ("concept_" + str(arguments.concept))
    participant = (concept / "participant").resolve(strict=True)
    output = concept / "attempts" / ("v_" + str(arguments.version))
    output.mkdir(parents=True, exist_ok=False)
    output = output.resolve()
    logs = concept / "attempts" / ("v_" + str(arguments.version) + "_run")
    logs.mkdir(parents=True, exist_ok=False)
    prompt = ("You are a fresh, isolated participant. Read TASK.md and the provided assets, solve the task, "
              "and place your complete submission in " + str(output) + ". You have at most 3600 seconds "
              "for this attempt. The task directory is read-only; use only your output directory for "
              "working files and final artifacts. Do not access sibling directories, external sources, "
              "or hidden evaluators. Do not delegate to other agents. Make and test the strongest "
              "submission you can within the allotted time; do not stop at an untested sketch. "
              "The scientific mission and required filenames are specified in TASK.md.")
    environment = os.environ.copy()
    environment["PATH"] = str(ROOT / "authoring" / "isolation") + os.pathsep + environment.get("PATH", "/usr/bin:/bin")
    environment["CUDA_VISIBLE_DEVICES"] = ""
    command = [str(RUNNER), "--model", "ultima-alpha", "--task-read-only", str(participant), str(output), prompt]
    before = digest_tree(participant)
    started = datetime.now(timezone.utc).isoformat()
    record = {"model": "ultima-alpha", "time_limit_seconds": 3600, "started_at": started,
              "participant": str(participant), "output": str(output), "runner": str(RUNNER),
              "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(), "command": command,
              "participant_sha256": before, "evaluator_sha256": digest_tree(concept / "evaluator"),
              "fresh_session": True, "ephemeral": True, "task_read_only": True,
              "transport": "allowlisted runner with deny-by-default Landlock/seccomp namespace transport",
              "transport_sha256": hashlib.sha256((ROOT / "authoring" / "isolation" / "bwrap").read_bytes()).hexdigest(),
              "status": "running"}
    (logs / "metadata.json").write_text(json.dumps(record, indent=2))
    began = time.monotonic()
    with (logs / "transcript.log").open("wb") as transcript:
        process = subprocess.Popen(command, cwd=participant, env=environment, stdout=transcript, stderr=subprocess.STDOUT,
                                   start_new_session=True, preexec_fn=resource_limits)
        record["pid"] = process.pid
        (logs / "metadata.json").write_text(json.dumps(record, indent=2))
        try:
            process.wait(timeout=3600)
            record["status"] = "finished"
        except subprocess.TimeoutExpired:
            record["status"] = "time_limit"
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    record.update(returncode=process.returncode, elapsed_seconds=time.monotonic() - began,
                  completed_at=datetime.now(timezone.utc).isoformat(), participant_unchanged=before == digest_tree(participant),
                  submission_sha256=digest_tree(output))
    (logs / "metadata.json").write_text(json.dumps(record, indent=2))
    print(json.dumps({key: record[key] for key in ("model", "status", "returncode", "elapsed_seconds", "participant_unchanged")}))


if __name__ == "__main__":
    main()
