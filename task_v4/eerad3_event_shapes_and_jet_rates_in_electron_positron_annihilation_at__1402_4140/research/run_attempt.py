import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--attempt", type=int)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    seal_path = concept / 'adversary' / f'frozen_generation_{arguments.generation}.json'
    seal = json.loads(seal_path.read_text())
    if seal['generation'] != arguments.generation:
        raise RuntimeError('wrong generation seal')
    for name, expected in seal['sha256'].items():
        path = concept / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('sealed participant or evaluator changed: ' + name)
    participant = (concept / "participant").resolve()
    attempt = arguments.attempt if arguments.attempt is not None else arguments.generation
    output = (concept / "attempts" / f"v_{attempt}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("fresh output directory is not empty")
    prefix = concept / "attempts" / f"v_{attempt}"
    evidence_path = prefix.with_suffix(".run.json")
    log_path = prefix.with_suffix(".runner.log")
    task_hashes = hashes(participant)
    launch_time = datetime.now(timezone.utc)
    deadline = launch_time + timedelta(seconds=3600)
    prompt = (f"Solve the task in TASK.md. Your participant directory is {participant}. "
              f"Write your complete runnable submission in {output}. "
              "You have up to one hour for investigation, implementation, and validation. "
              "The participant assets are read-only; use your output directory for all work. "
              "No hidden evaluator, generation-side data, or previous attempt is available. "
              "Focus on the executable artifact, not a prose-only proposal. "
              "Run sensible local validation before finishing. Do not access files outside "
              "the allowlisted task, output, and system runtime. "
              f"The hard wall deadline is {deadline.isoformat()}, including startup and tool overhead.")
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only",
               str(participant), str(output), prompt]
    metadata = {"concept": arguments.concept, "generation": arguments.generation, "attempt": attempt,
                "model": "ultima-alpha", "authoring_limit_seconds": 3600,
                "runner": str(RUNNER), "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
                "launcher_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "generation_seal_sha256": hashlib.sha256(seal_path.read_bytes()).hexdigest(),
                "hard_deadline_utc": deadline.isoformat(),
                "participant_read_only": True, "initial_output_empty": True,
                "allowlist": [str(participant), str(output)], "command": command,
                "participant_sha256_before": task_hashes,
                "started_at": launch_time.isoformat(), "status": "running"}
    evidence_path.write_text(json.dumps(metadata, indent=2) + "\n")
    environment = os.environ.copy()
    environment.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=environment)
        metadata["pid"] = process.pid
        evidence_path.write_text(json.dumps(metadata, indent=2) + "\n")
        try:
            returncode = process.wait(timeout=3600)
            metadata.update(status="exited", returncode=returncode, timed_out=False)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            metadata.update(status="authoring_timeout", returncode=process.returncode, timed_out=True)
    metadata.update(wall_seconds=time.monotonic() - started,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    participant_unchanged=hashes(participant) == task_hashes,
                    submission_sha256=hashes(output))
    evidence_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({key: value for key, value in metadata.items()
                      if key not in {"participant_sha256_before", "submission_sha256", "command"}}, indent=2))


if __name__ == "__main__":
    main()
