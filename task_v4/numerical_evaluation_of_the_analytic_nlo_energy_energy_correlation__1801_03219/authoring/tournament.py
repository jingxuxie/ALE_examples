import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def digest(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--attempt", type=int, default=1)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    participant = concept / "participant"
    attempt = concept / "attempts" / f"v_{arguments.attempt}"
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise ValueError("fresh output must be empty")
    transcript = attempt.with_suffix(".log")
    manifest = attempt.with_suffix(".run.json")
    before = digest(participant)
    record = {
        "model": "ultima-alpha", "effort": "high", "time_limit_seconds": 3600,
        "generation": arguments.generation, "attempt": arguments.attempt,
        "initial_output_empty": True, "participant_sha256": before,
        "allowlisted_paths": [str(participant), str(attempt)],
        "task_read_only": True, "ephemeral": True, "web_search": "disabled",
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "running",
    }
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    prompt = (
        f"Read TASK.md and solve the participant task. Only the assets in {participant} "
        f"are available. Write the executable artifact required by TASK.md into {attempt}. "
        "That output directory is initially empty. You have at most 3600 seconds (60 minutes), not ten minutes. "
        "You may finalize early if successful; otherwise use the remaining budget to improve your artifact. "
        "Work independently; no internet or outside task files are available. "
        "Focus on the requested artifact, not a report. The participant files are read-only."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high",
               "--task-read-only", str(participant), str(attempt), prompt]
    started = time.monotonic()
    with transcript.open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = process.wait(timeout=3600)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    record.update({
        "status": "finished", "elapsed_seconds": time.monotonic() - started,
        "timed_out": timed_out, "returncode": returncode,
        "participant_unchanged": before == digest(participant),
        "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "submission_sha256": digest(attempt),
    })
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: value for key, value in record.items()
                      if not key.endswith("sha256")}, indent=2))


if __name__ == "__main__":
    main()
