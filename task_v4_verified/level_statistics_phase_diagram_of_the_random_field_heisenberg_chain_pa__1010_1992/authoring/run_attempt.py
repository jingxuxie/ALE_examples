import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def tree_digest(path):
    digest = hashlib.sha256()
    for entry in sorted(path.rglob("*")):
        if entry.is_file() and "__pycache__" not in entry.parts:
            if entry.is_symlink():
                raise ValueError("Symlink in task or submission tree: " + str(entry))
            digest.update(str(entry.relative_to(path)).encode())
            digest.update(entry.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--participant", type=Path)
    arguments = parser.parse_args()
    concept = arguments.concept.resolve()
    participant = (arguments.participant or concept / "participant").resolve()
    attempt = concept / "attempts" / ("v_" + str(arguments.attempt))
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise ValueError("Fresh attempt output is not empty")
    stem = concept / "attempts" / ("v_" + str(arguments.attempt))
    runner = Path("/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh")
    prompt = ("You have at most one hour. Read TASK.md in the current participant directory and solve the task. "
              "All provided assets are here and are read-only. Investigate independently; implement and test your submission. "
              "Write the final artifact and any implementation assets only to " + str(attempt) +
              ". That output directory is initially empty. Do not stop at a proposal. No internet access is available.")
    command = [str(runner), "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(attempt), prompt]
    metadata = {"model": "ultima-alpha", "attempt": arguments.attempt, "generation": arguments.generation,
                "limit_seconds": 3600, "participant": str(participant), "output": str(attempt),
                "command": command, "started_utc": datetime.now(timezone.utc).isoformat(),
                "participant_sha256_before": tree_digest(participant), "initial_output_empty": True,
                "main_context_shared": False, "evaluator_access": False, "network_access": False}
    metadata_path = stem.with_suffix(".run.json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    started = time.monotonic()
    with stem.with_suffix(".stdout.log").open("wb") as stdout, stem.with_suffix(".stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
        metadata["pid"] = process.pid
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
        try:
            returncode = process.wait(timeout=3600)
            metadata["timed_out"] = False
        except subprocess.TimeoutExpired:
            metadata["timed_out"] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    metadata.update(returncode=returncode, seconds=time.monotonic() - started,
                    ended_utc=datetime.now(timezone.utc).isoformat(),
                    participant_sha256_after=tree_digest(participant), submission_sha256=tree_digest(attempt))
    metadata["participant_unchanged"] = metadata["participant_sha256_after"] == metadata["participant_sha256_before"]
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata), flush=True)


if __name__ == "__main__":
    main()
