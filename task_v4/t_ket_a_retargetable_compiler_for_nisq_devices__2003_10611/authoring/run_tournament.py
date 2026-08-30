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


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int)
    parser.add_argument("--generation", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--participant")
    arguments = parser.parse_args()
    concept = ROOT / f"concept_{arguments.concept}"
    participant = Path(arguments.participant).resolve() if arguments.participant else concept / "participant"
    output = concept / "attempts" / f"v_{arguments.generation}"
    output.mkdir(parents=True, exist_ok=True)
    if list(output.iterdir()):
        raise RuntimeError("fresh output directory must be empty")
    started_at = datetime.datetime.now(datetime.timezone.utc)
    deadline = started_at + datetime.timedelta(seconds=3600)
    prompt = (f"Solve the professional task in TASK.md. The participant directory is {participant}; "
              f"the initially empty writable submission directory is {output}. "
              "Read the task and assets, then investigate, implement, and test your solution autonomously. "
              "Write all deliverables and development files inside the submission directory. "
              "You have a maximum of 3600 seconds (one hour) of wall-clock time for this attempt; "
              f"the hard deadline is {deadline.isoformat()} (UTC), including startup. "
              "use the time for substantive implementation and validation. "
              "Your final artifact, not a plan or explanation, is evaluated. "
              "The participant directory is read-only. Only participant assets, your output directory, "
              "and standard runtime/toolchain paths are authorized. Do not use network, other tasks, "
              "other submissions, hidden evaluators, or subagents. "
              "Before solving, confirm that TASK.md is readable and that ../evaluator/hidden cannot be read; "
              "do not probe any other private paths. Do not stop merely because the baseline runs.")
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "xhigh", "--task-read-only",
               str(participant), str(output), prompt]
    runner_source = RUNNER.read_bytes()
    runner_snapshot = concept / "attempts" / f"v_{arguments.generation}.runner.sh"
    runner_snapshot.write_bytes(runner_source)
    metadata = {"model": "ultima-alpha", "effort": "xhigh", "limit_seconds": 3600,
                "participant": str(participant), "output": str(output), "initial_output_empty": True,
                "fresh_session": True, "ephemeral": True, "network": False, "task_access": "read",
                "runner": str(RUNNER), "runner_sha256": hashlib.sha256(runner_source).hexdigest(),
                "runner_snapshot": str(runner_snapshot),
                "participant_hashes_before": hashes(participant), "command": command,
                "started_at": started_at.isoformat(), "deadline_utc": deadline.isoformat()}
    metadata_path = concept / "attempts" / f"v_{arguments.generation}.metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    started = time.monotonic()
    with (concept / "attempts" / f"v_{arguments.generation}.log").open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        metadata["pid"] = process.pid
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
        try:
            exit_code = process.wait(timeout=3600)
            metadata["timed_out"] = False
        except subprocess.TimeoutExpired:
            metadata["timed_out"] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                exit_code = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                exit_code = process.wait()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    metadata["exit_code"] = exit_code
    metadata["elapsed_seconds"] = time.monotonic() - started
    metadata["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metadata["participant_hashes_after"] = hashes(participant)
    metadata["participant_unchanged"] = metadata["participant_hashes_before"] == metadata["participant_hashes_after"]
    metadata["submission_hashes"] = hashes(output)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({key: value for key, value in metadata.items() if not key.endswith("hashes") and "hashes_" not in key}, indent=2))


if __name__ == "__main__":
    main()
