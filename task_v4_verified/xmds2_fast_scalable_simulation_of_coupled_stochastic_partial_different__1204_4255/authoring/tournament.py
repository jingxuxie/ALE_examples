import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--participant")
    parser.add_argument("--attempt", default="v_1")
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    participant = Path(arguments.participant).resolve() if arguments.participant else concept / "participant"
    if not re.fullmatch(r"v_[1-9][0-9]*(?:_[a-z0-9]+)?", arguments.attempt):
        raise ValueError("invalid attempt name")
    output = concept / "attempts" / arguments.attempt
    output.mkdir(parents=True, exist_ok=True)
    record_path = concept / "attempts" / (arguments.attempt + ".run.json")
    if list(output.iterdir()) or record_path.exists():
        raise ValueError("fresh output and run record must not already contain anything")
    prompt = f"Solve TASK.md using only the provided participant package. Write your final submission and every required asset in the empty writable output directory {output}. This directory is your only persistent writable workspace. You have at most one hour; decide your own investigation and solution strategy. Do not access external network resources."
    if arguments.concept == "concept_2":
        prompt += " Name your final JSON witness submission.json."
    elif arguments.concept == "concept_3":
        prompt += " Name your final JSON control artifact control.json."
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only", str(participant), str(output), prompt]
    record = {"model": "ultima-alpha", "effort": "high", "generation": arguments.generation, "limit_seconds": 3600, "started_at": datetime.now(timezone.utc).isoformat(), "output_empty_at_start": True, "participant_access": "read-only", "output_access": "read-write", "privileged_mounts": [], "command": command, "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(), "participant_sha256": hashes(participant), "evaluator_sha256": hashes(concept / "evaluator"), "status": "running"}
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    started = time.monotonic()
    with (concept / "attempts" / (arguments.attempt + ".session.log")).open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.wait(timeout=3600)
            record["status"] = "finished"
        except subprocess.TimeoutExpired:
            record["status"] = "time_limit"
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    record.update(returncode=process.returncode, elapsed_seconds=time.monotonic() - started, finished_at=datetime.now(timezone.utc).isoformat(), submission_sha256=hashes(output))
    record["participant_unchanged"] = hashes(participant) == record["participant_sha256"]
    record["evaluator_unchanged"] = hashes(concept / "evaluator") == record["evaluator_sha256"]
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: value for key, value in record.items() if not key.endswith("sha256") and key != "command"}, indent=2))


if __name__ == "__main__":
    main()
