import argparse
from datetime import datetime, timezone
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
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", required=True, type=int)
    parser.add_argument("--attempt", default="v_1")
    parser.add_argument("--generation-root", type=Path)
    arguments = parser.parse_args()
    concept = arguments.generation_root.resolve() if arguments.generation_root else ROOT / f"concept_{arguments.concept}"
    participant = concept / "participant"
    attempts = concept / "attempts"
    attempts.mkdir(exist_ok=True)
    output = attempts / arguments.attempt
    output.mkdir()
    metadata_path = attempts / (arguments.attempt + ".run.json")
    metadata = {
        "model": "ultima-alpha", "reasoning_effort": "high", "time_limit_seconds": 3600,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "participant_read_only": True, "output_initially_empty": not any(output.iterdir()),
        "participant": str(participant), "output": str(output),
        "participant_sha256": hashes(participant),
        "allowed_task_artifacts": ["participant/", f"attempts/{arguments.attempt}/"],
        "external_network": "disabled by runner", "ephemeral": True,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    prompt = f"Read TASK.md and solve the participant task independently. Write your runnable submission into {output}. You have at most one hour. The supplied participant directory is read-only; only the initially empty output directory is writable. Use only participant assets and normal system libraries. Do not inspect other task directories, request evaluator feedback, use network access, or launch other agents. You may run your own local tests. Finish with the required executable or artifact in the output directory."
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only", str(participant), str(output), prompt]
    started = time.monotonic()
    with (attempts / (arguments.attempt + ".log")).open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return_code = process.wait(timeout=3600)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait()
    metadata.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started, timed_out=timed_out, exit_code=return_code, submission_sha256=hashes(output))
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({key: metadata[key] for key in ("model", "elapsed_seconds", "timed_out", "exit_code")}))


if __name__ == "__main__":
    main()
