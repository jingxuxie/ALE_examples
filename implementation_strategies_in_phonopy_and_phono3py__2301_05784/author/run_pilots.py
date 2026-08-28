"""Run independently allowlisted, time-limited model attempts and retain evidence."""

import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def tree_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(directory)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def run_one(concept, stage, limit, model):
    concept_dir = ROOT / "concepts" / concept
    participant = concept_dir / "participant"
    if stage == "pilot":
        attempt = concept_dir / "attempt"
    else:
        participant = concept_dir / stage / "participant"
        attempt = concept_dir / stage / "attempt"
    attempt.mkdir(parents=True, exist_ok=True)
    if any(attempt.iterdir()):
        raise RuntimeError(f"Refusing nonempty fresh attempt: {attempt}")
    if not (participant / "TASK.md").exists():
        raise FileNotFoundError(participant / "TASK.md")
    log_dir = ROOT / "author" / "pilot_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"{concept}_{stage}.log"
    status = log_dir / f"{concept}_{stage}.json"
    prompt = (
        f"Read TASK.md and the public workspace contract, then complete the mission. "
        f"Write your executable Python solution as {attempt}/solve.py and any helper "
        f"files only in {attempt}. The grader invokes python solve.py INPUT.npz OUTPUT.npz. "
        f"The participant directory is read-only. It and your empty attempt directory "
        f"are the only task directories available. Do not attempt to access other "
        f"directories or network services. Use the available system Python, NumPy, "
        f"SciPy and public assets. You have up to {limit} seconds; use the time to "
        f"implement and test the scientific core, not merely a plan. You may inspect "
        f"the weak baseline but should repair or replace it. Include a short factual "
        f"solution.md listing what you implemented and tested. Do not ask the user "
        f"questions. Start by checking that the numerical environment works. "
        f"If system NumPy reports missing libblas/liblapack in the minimal sandbox, "
        f"set LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/blas:/usr/lib/x86_64-linux-gnu/lapack "
        f"for Python commands; this is an environment workaround, not part of the task."
    )
    command = [str(RUNNER), "--model", model, "--effort", "high",
               "--task-read-only", str(participant), str(attempt), prompt]
    evidence = {
        "concept": concept, "stage": stage, "model": model,
        "time_limit_seconds": limit, "runner": str(RUNNER),
        "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
        "participant": str(participant), "attempt": str(attempt),
        "participant_sha256_before": tree_digest(participant),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "command": command, "allowlist": [str(participant), str(attempt)],
        "previous_attempt_access": False,
    }
    status.write_text(json.dumps(evidence, indent=2) + "\n")
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = "/usr/lib/x86_64-linux-gnu/blas:/usr/lib/x86_64-linux-gnu/lapack"
    for key in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"]:
        environment[key] = "1"
    started = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL,
                                   start_new_session=True, env=environment)
        evidence["pid"] = process.pid
        status.write_text(json.dumps(evidence, indent=2) + "\n")
        try:
            returncode = process.wait(timeout=limit)
            stop_reason = "finished"
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            returncode = process.returncode
            stop_reason = "time_limit"
    evidence.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - started,
        "returncode": returncode, "stop_reason": stop_reason,
        "has_solution": (attempt / "solve.py").is_file(),
        "participant_sha256_after": tree_digest(participant),
        "attempt_sha256": tree_digest(attempt),
    })
    status.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence), flush=True)
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concepts", nargs="+")
    parser.add_argument("--stage", default="pilot")
    parser.add_argument("--limit", type=int, default=3600)
    parser.add_argument("--model", default="ultima-alpha")
    args = parser.parse_args()
    if args.limit > 3600:
        raise ValueError("Pilot limit exceeds user-specified one hour")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(args.concepts)) as executor:
        futures = [executor.submit(run_one, concept, args.stage, args.limit, args.model)
                   for concept in args.concepts]
        results = [future.result() for future in futures]
    destination = ROOT / "author" / "pilot_logs" / f"{args.stage}_batch.json"
    destination.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
