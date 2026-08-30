import argparse
import datetime
import hashlib
import json
import os
import signal
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]


def fingerprint(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int, choices=[1, 2, 3])
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--participant", type=Path)
    arguments = parser.parse_args()
    concept = ROOT / f"concept_{arguments.concept}"
    participant = (arguments.participant or concept / "participant").resolve(strict=True)
    attempts = concept / "attempts"
    output = attempts / f"v_{arguments.attempt}"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("a fresh attempt requires an empty output directory")
    stem = attempts / f"v_{arguments.attempt}"
    runner = REPOSITORY / "run_allowlisted_codex.sh"
    prompt = f"You are an independent participant. Read TASK.md and solve the task using only the supplied participant assets. You have a maximum of 3600 seconds of development time. The writable output directory is {output}. First run `python3 workspace/audit_isolation.py {output}` to record the access check. Write your final executable/artifact and supporting files into that output directory as specified by TASK.md. The participant directory is read-only; use the output directory for development. Work autonomously and do not request access to any other directories or the internet."
    prompt += " Use file-relative paths for all submitted artifacts; your submission may be relocated to an immutable scoring snapshot after this session ends."
    command = [str(runner), "--model", "ultima-alpha", "--task-read-only", str(participant), str(output), prompt]
    manifest = {"model": "ultima-alpha", "limit_seconds": 3600, "participant": str(participant), "output": str(output), "runner": str(runner), "runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(), "command": command, "fresh_ephemeral": True, "participant_read_only": True, "output_initially_empty": True, "participant_sha256_before": fingerprint(participant), "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    evaluation_root = participant.parent / "evaluator"
    manifest["evaluator"] = str(evaluation_root)
    manifest["evaluator_sha256_before"] = fingerprint(evaluation_root)
    Path(str(stem) + ".launch.json").write_text(json.dumps(manifest, indent=2))
    Path(str(stem) + ".prompt.txt").write_text(prompt + "\n")
    started = time.monotonic()
    started_epoch = time.time()
    timed_out = False
    with Path(str(stem) + ".log").open("wb") as logfile:
        process = subprocess.Popen(command, cwd=participant, stdin=subprocess.DEVNULL, stdout=logfile, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait()
    agent_elapsed = time.monotonic() - started
    snapshot = attempts / f"v_{arguments.attempt}_frozen"
    excluded = []

    def exclude_late_files(directory, names):
        ignored = []
        for name in names:
            path = Path(directory) / name
            if name in (".git", ".agents", ".codex", "__pycache__"):
                ignored.append(name)
            elif path.is_file() and path.stat().st_mtime > started_epoch + 3600:
                ignored.append(name)
                excluded.append(str(path.relative_to(output)))
        return ignored

    shutil.copytree(output, snapshot, symlinks=True, ignore=exclude_late_files)
    manifest.update(returncode=returncode, timed_out=timed_out, elapsed_seconds=agent_elapsed, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), participant_sha256_after=fingerprint(participant), scoring_snapshot=str(snapshot), post_deadline_files_excluded=excluded, snapshot_sha256=fingerprint(snapshot))
    manifest["participant_unchanged"] = manifest["participant_sha256_before"] == manifest["participant_sha256_after"]
    manifest["evaluator_sha256_after"] = fingerprint(evaluation_root)
    manifest["evaluator_unchanged"] = manifest["evaluator_sha256_before"] == manifest["evaluator_sha256_after"]
    Path(str(stem) + ".launch.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({key: value for key, value in manifest.items() if "sha256_" not in key and key != "command"}, indent=2))


if __name__ == "__main__":
    main()
