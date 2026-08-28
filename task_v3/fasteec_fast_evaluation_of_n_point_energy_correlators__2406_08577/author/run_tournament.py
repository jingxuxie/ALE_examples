import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def run_one(kind, version):
    concept = ROOT / "pilots" / kind if version == "pilot" else ROOT / "ratchets" / kind / version
    participant = concept / "participant"
    attempt = concept / "attempt"
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError("Fresh attempt directory is not empty: " + str(attempt))
    for required in [participant / "TASK.md", participant / "input" / "CONTRACT.md", participant / "input" / "sample.json"]:
        if not required.is_file() or "PENDING AUTHOR" in required.read_text():
            raise RuntimeError("Incomplete participant package: " + str(required))
    logs = ROOT / "author" / "runs"
    logs.mkdir(exist_ok=True)
    run_id = kind + "_" + version
    prompt = (
        "Read TASK.md and input/CONTRACT.md, then solve the task autonomously. "
        "Your only task files are in " + str(participant) + ". "
        "Write your complete submission as " + str(attempt / "solve.py") + ", "
        "with any supporting source files or cached binaries in " + str(attempt) + ". "
        "The entrypoint must accept --input JOB.json --output RESULT.json. "
        "The participant directory is read-only; use your attempt directory for all writes. "
        "You have up to one hour. Use the available tools, implement the substantive numerical work, "
        "and validate on public inputs. Do not ask for clarification or access outside these directories. "
        "No internet access is available. Finish with a concise account of what works and any limitations."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "xhigh", "--task-read-only", str(participant), str(attempt), prompt]
    record = {"kind": kind, "version": version, "model": "ultima-alpha", "effort": "xhigh", "time_limit_seconds": 3600, "participant": str(participant), "attempt": str(attempt), "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(), "public_hashes": {str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest() for path in participant.rglob("*") if path.is_file()}, "started_unix": time.time()}
    begin = time.monotonic()
    with (logs / (run_id + ".log")).open("w") as stream:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        record["pid"] = process.pid
        (logs / (run_id + ".running.json")).write_text(json.dumps(record, indent=2))
        try:
            record["returncode"] = process.wait(timeout=3600)
            record["timed_out"] = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            record["returncode"] = process.returncode
            record["timed_out"] = True
    record["wall_seconds"] = time.monotonic() - begin
    record["finished_unix"] = time.time()
    record["submission_exists"] = (attempt / "solve.py").is_file()
    (logs / (run_id + ".json")).write_text(json.dumps(record, indent=2))
    print(json.dumps({key: record[key] for key in ["kind", "version", "returncode", "timed_out", "wall_seconds", "submission_exists"]}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kinds", nargs="+", required=True)
    parser.add_argument("--version", default="pilot")
    arguments = parser.parse_args()
    with ThreadPoolExecutor(max_workers=len(arguments.kinds)) as executor:
        futures = [executor.submit(run_one, kind, arguments.version) for kind in arguments.kinds]
        for future in futures:
            future.result()


if __name__ == "__main__":
    main()
