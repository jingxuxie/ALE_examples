import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def snapshot(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--version", default="initial")
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    participant = concept / "participant" if arguments.version == "initial" else concept / "versions" / arguments.version / "participant"
    attempt = concept / "attempt" if arguments.version == "initial" else concept / "versions" / arguments.version / "attempt"
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError("Refusing to reuse a nonempty attempt directory")
    records = concept / "private" / "runs"
    records.mkdir(parents=True, exist_ok=True)
    prompt = ("Work autonomously for up to one hour to solve the mission in TASK.md. Read the interface contract and inspect the supplied workspace. "
              "The task directory is read-only. Put your complete implementation, tests, and all scratch work in " + str(attempt) + ". "
              "Your required entry point is " + str(attempt / "solve.py") + ". Do not stop at a plan or explanation: implement and test the strongest general solution you can. "
              "You have only this task directory and your empty attempt directory, plus installed system runtimes. Do not use network access, outside artifacts, or other agents.")
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only", str(participant), str(attempt), prompt]
    metadata = {"model": "ultima-alpha", "effort": "high", "limit_seconds": 3600, "version": arguments.version,
                "participant": str(participant), "attempt": str(attempt), "runner": str(RUNNER), "prompt": prompt,
                "started_unix": time.time(), "participant_before": snapshot(participant), "empty_attempt_verified": True}
    metadata_path = records / f"{arguments.version}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    with (records / f"{arguments.version}.log").open("w") as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        metadata["process_id"] = process.pid
        metadata_path.write_text(json.dumps(metadata, indent=2))
        try:
            status = process.wait(timeout=3600)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            status = 124
    metadata.update(returncode=status, timed_out=timed_out, ended_unix=time.time(), participant_after=snapshot(participant),
                    deliverables=snapshot(attempt))
    metadata["participant_unchanged"] = metadata["participant_before"] == metadata["participant_after"]
    metadata["elapsed_seconds"] = metadata["ended_unix"] - metadata["started_unix"]
    metadata_path.write_text(json.dumps(metadata, indent=2))
    print(json.dumps({key: metadata[key] for key in ["model", "version", "returncode", "elapsed_seconds", "timed_out", "participant_unchanged"]}), flush=True)


if __name__ == "__main__":
    main()
