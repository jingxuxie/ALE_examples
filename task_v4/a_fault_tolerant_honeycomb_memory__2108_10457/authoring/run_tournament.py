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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--attempt-index", type=int)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    participant = concept / "participant"
    attempt_index = arguments.attempt_index or arguments.generation
    output = concept / "attempts" / f"v_{attempt_index}"
    output.mkdir(parents=True, exist_ok=False)
    record_path = concept / "attempts" / f"v_{attempt_index}_runner.json"
    log_path = concept / "attempts" / f"v_{attempt_index}.log"
    prompt = (f"Solve the task in {participant / 'TASK.md'}. You have up to one hour. "
              f"Read only the supplied participant assets and place your complete submission in {output}. "
              "The participant tree is read-only; write all code, temporary work, and caches inside your output directory. "
              "You may use a persistent shell session if command sandbox startup is slow. "
              "Do not search for other task directories or use external data. Follow TASK.md's executable interface. "
              "Use the available time to investigate, implement, and test your best solution. "
              "A submission that merely copies the baseline does not meet an improvement objective.")
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(output), prompt]
    start = time.monotonic()
    record = {"concept": arguments.concept, "generation": arguments.generation, "attempt_index": attempt_index,
              "model": "ultima-alpha", "effort": "high", "limit_seconds": 3600,
              "started_utc": datetime.now(timezone.utc).isoformat(), "command": command,
              "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
              "participant_sha256": json.loads((concept / "evaluator" / "frozen.json").read_text())}
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        record["process_id"] = process.pid
        record_path.write_text(json.dumps(record, indent=2) + "\n")
        try:
            process.wait(timeout=3600)
            record["timed_out"] = False
        except subprocess.TimeoutExpired:
            record["timed_out"] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    record["returncode"] = process.returncode
    record["elapsed_seconds"] = time.monotonic() - start
    record["finished_utc"] = datetime.now(timezone.utc).isoformat()
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: value for key, value in record.items() if key not in {"command", "participant_sha256"}}, indent=2))


if __name__ == "__main__":
    main()
