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


def manifest(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*") if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot")
    parser.add_argument("--round", default="initial")
    parser.add_argument("--participant")
    parser.add_argument("--attempt")
    args = parser.parse_args()
    pilot = ROOT / "pilots" / args.pilot
    participant = Path(args.participant).resolve() if args.participant else pilot / "participant"
    attempt = Path(args.attempt).resolve() if args.attempt else pilot / "attempt"
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError(f"Fresh attempt directory is not empty: {attempt}")
    evidence = pilot / "private" / "runs" / args.round
    evidence.mkdir(parents=True, exist_ok=True)
    prompt = (
        f"Solve the mission in TASK.md. Read input/ and workspace/ as needed. "
        f"You have up to one hour. Write the complete executable submission and any needed files into {attempt}. "
        f"Keep the task directory read-only. Your only task-artifact access is {participant} and {attempt}; "
        f"no private references or earlier attempts are available. Test your solution on the provided input, "
        f"and make solve.py follow the documented interface. Do not stop at a plan or claim success without an implementation."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only", str(participant), str(attempt), prompt]
    before = manifest(participant)
    started = time.monotonic()
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    with (evidence/"transcript.log").open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   env=environment, start_new_session=True)
        (evidence/"started.json").write_text(json.dumps({"pid":process.pid, "model":"ultima-alpha", "started_unix":time.time(), "limit_seconds":3600})+"\n")
        status = "completed"
        try:
            returncode = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            status = "time_limit"
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    result = dict(model="ultima-alpha", reasoning_effort="high", limit_seconds=3600,
                  elapsed_seconds=time.monotonic()-started, returncode=returncode, status=status,
                  command=command, participant=str(participant), attempt=str(attempt),
                  participant_unchanged=before == manifest(participant),
                  participant_sha256=before, attempt_sha256=manifest(attempt),
                  isolation="provided allowlisted runner, task read-only, fresh empty attempt, no web, no approvals, ephemeral session")
    (evidence/"launch.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({key:value for key,value in result.items() if not key.endswith("sha256")}), flush=True)


if __name__ == "__main__":
    main()
