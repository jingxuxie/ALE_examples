import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts}


def run(concept_number, attempt_number):
    concept = ROOT / f"concept_{concept_number}"
    participant = concept / "participant"
    output = concept / "attempts" / f"v_{attempt_number}"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError(f"fresh output is not empty: {output}")
    metadata_path = concept / "attempts" / f"v_{attempt_number}_run.json"
    log_path = concept / "attempts" / f"v_{attempt_number}.log"
    prompt = (
        "You are a fresh independent participant. Read TASK.md in the current directory and solve the task. "
        f"Write your final submission and any supporting files into {output}. "
        "You have at most 3600 seconds (one hour) of wall-clock time. You may finish sooner when satisfied. "
        "Only the participant assets and this initially empty output directory are available; "
        "the participant directory is read-only. Do not access sibling directories, evaluator files, "
        "other attempts, or outside services. Do not spawn other model sessions. "
        "Use the provided executable interface and resource limits. Validate your work using the public "
        "assets, and leave the requested artifact even if the full target seems difficult. "
        "The final reply should briefly identify what was submitted."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(output), prompt]
    record = {"model": "ultima-alpha", "reasoning_effort": "high", "wall_limit_seconds": 3600,
              "participant": str(participant), "output": str(output), "output_initially_empty": True,
              "runner": str(RUNNER), "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
              "participant_hashes_before": hashes(participant), "started_unix": time.time(),
              "fresh_context": True, "participant_read_only": True, "prompt": prompt,
              "status": "running"}
    metadata_path.write_text(json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    with log_path.open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        timed_out = False
        try:
            returncode = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    record.update({"elapsed_seconds": time.monotonic() - started, "returncode": returncode,
                   "timed_out": timed_out, "participant_hashes_after": hashes(participant),
                   "status": "finished", "output_files": hashes(output)})
    record["participant_unchanged"] = record["participant_hashes_before"] == record["participant_hashes_after"]
    metadata_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: value for key, value in record.items()
                      if key not in ("participant_hashes_before", "participant_hashes_after", "output_files", "prompt")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", type=int, required=True)
    parser.add_argument("--attempt", type=int, default=1)
    arguments = parser.parse_args()
    run(arguments.concept, arguments.attempt)
