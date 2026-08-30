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


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def manifest(directory, allow_symlinks=False):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            if not allow_symlinks:
                raise ValueError("symlink in participant assets: " + str(path))
            result[str(path.relative_to(directory))] = {"symlink": os.readlink(path)}
            continue
        if path.is_file() and "__pycache__" not in path.parts:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1048576), b""):
                    digest.update(chunk)
            result[str(path.relative_to(directory))] = digest.hexdigest()
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def launch(concept_name, attempt_name, seconds):
    concept = ROOT / concept_name
    participant = concept / "participant"
    output = concept / "attempts" / attempt_name
    if output.exists() and any(output.iterdir()):
        raise ValueError("fresh output directory must be empty: " + str(output))
    output.mkdir(parents=True, exist_ok=True)
    logs = concept / "attempts" / (attempt_name + "_audit")
    if logs.exists():
        raise ValueError("audit directory already exists; do not overwrite an attempt")
    logs.mkdir()
    hashes = manifest(participant)
    prompt = (
        "Solve the research task described in TASK.md using only the provided participant assets. "
        "This is a completely fresh, isolated attempt. The participant directory is read-only; "
        "write all code, intermediate experiments, and final deliverables under " + str(output) + ". "
        "You have a wall-clock limit of " + str(seconds) + " seconds. "
        "Use the installed CPU numerical libraries, run your own checks, and produce the actual required artifact. "
        "Do not invoke other agents or external services. Do not seek evaluator, adversary, champion, or other attempt directories. "
        "A report alone is not a submission. If you finish early, leave your best complete submission in the output directory."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only", str(participant), str(output), prompt]
    audit = {
        "concept": concept_name,
        "attempt": attempt_name,
        "model": "ultima-alpha",
        "effort": "high",
        "wall_limit_seconds": seconds,
        "started_utc": timestamp(),
        "state": "running",
        "empty_output_at_launch": True,
        "participant_read_only": True,
        "read_allowlist_task": str(participant),
        "writable_output": str(output),
        "excluded": ["evaluator", "adversary", "champions", "other_attempts", "authoring", "prior_task_versions"],
        "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
        "command": command,
        "participant_sha256": hashes,
    }
    write_json(logs / "audit.json", audit)
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PYTHONUNBUFFERED": "1"})
    started = time.monotonic()
    with (logs / "session.log").open("wb") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=environment, start_new_session=True)
        audit["pid"] = process.pid
        write_json(logs / "audit.json", audit)
        try:
            return_code = process.wait(timeout=seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait()
    after = manifest(participant)
    audit.update({
        "state": "finished",
        "finished_utc": timestamp(),
        "elapsed_seconds": time.monotonic() - started,
        "return_code": return_code,
        "timed_out": timed_out,
        "participant_unchanged": after == hashes,
        "submission_files": manifest(output, allow_symlinks=True),
    })
    write_json(logs / "audit.json", audit)
    print(json.dumps({key: audit[key] for key in ["concept", "attempt", "elapsed_seconds", "return_code", "timed_out", "participant_unchanged"]}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", choices=["concept_1", "concept_2", "concept_3"])
    parser.add_argument("attempt")
    parser.add_argument("--seconds", type=int, default=3600)
    arguments = parser.parse_args()
    if arguments.seconds < 1 or arguments.seconds > 3600:
        raise ValueError("fresh agent limit must not exceed one hour")
    launch(arguments.concept, arguments.attempt, arguments.seconds)


if __name__ == "__main__":
    main()
