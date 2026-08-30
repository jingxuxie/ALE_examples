import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def manifest(directory):
    contents = {}
    for path in sorted(directory.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError(f"symlink not allowed in frozen assets: {path}")
        if path.is_file():
            contents[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return contents


def launch(concept_number, generation, attempt_number=None):
    attempt_number = generation if attempt_number is None else attempt_number
    if attempt_number < 1:
        raise ValueError("attempt number must be positive")
    concept = ROOT / f"concept_{concept_number}"
    participant = concept / "participant"
    output = concept / "attempts" / f"v_{attempt_number}"
    evidence = concept / "attempts" / f"v_{attempt_number}_evidence"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("attempt output is not empty")
    evidence.mkdir(parents=True, exist_ok=False)
    before = manifest(participant)
    frozen = {"participant": before, "evaluator": manifest(concept / "evaluator")}
    (evidence / "frozen_manifest.json").write_text(json.dumps(frozen, indent=2) + "\n")
    staging = Path(tempfile.mkdtemp(prefix=f"cascade-c{concept_number}-g{generation}-v{attempt_number}-"))
    run_participant = staging / "participant"
    run_output = staging / "attempts" / f"v_{attempt_number}"
    shutil.copytree(participant, run_participant, ignore=shutil.ignore_patterns("__pycache__"))
    run_output.mkdir(parents=True)
    assert manifest(run_participant) == before
    start_datetime = datetime.now(timezone.utc)
    deadline = start_datetime + timedelta(seconds=3600)
    prompt = (
        f"Solve the scientific task in TASK.md. You have up to one hour (3600 wall seconds), "
        f"with deadline {deadline.isoformat()}. Your only task assets are in {run_participant}. "
        f"Your initially empty writable output directory is {run_output}. "
        f"Place the final artifact and every dependency requested by TASK.md in {run_output}. "
        "You may use this output directory for investigation and working files. Task assets are read-only. "
        "Only the participant assets and your output directory are authorized; do not use the network, "
        "other task directories, private evaluators, or other sessions. Investigate and validate your "
        "submission within the deadline. Do not stop at a plan."
    )
    command = [str(RUNNER), "--model", "ultima-alpha", "--effort", "high", "--task-read-only", str(run_participant), str(run_output), prompt]
    metadata = {
        "model": "ultima-alpha", "effort": "high", "limit_seconds": 3600,
        "concept": concept_number, "generation": generation, "attempt_number": attempt_number, "output_initially_empty": True,
        "started_utc": start_datetime.isoformat(), "deadline_utc": deadline.isoformat(),
        "participant": str(participant), "output": str(output),
        "staged_participant": str(run_participant), "staged_output": str(run_output),
        "command": command, "task_read_only": True, "staging_reason": "local files avoid shared mount sandbox startup stalls"
    }
    metadata_path = evidence / "launch.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    started = time.monotonic()
    with (evidence / "transcript.log").open("w") as transcript:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=transcript, stderr=subprocess.STDOUT, start_new_session=True)
        metadata["pid"] = process.pid
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
        timed_out = False
        try:
            process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    metadata.update(returncode=process.returncode, elapsed_seconds=time.monotonic() - started, timed_out=timed_out, ended_utc=datetime.now(timezone.utc).isoformat())
    shutil.copytree(run_output, output, symlinks=True, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".git", ".agents", ".codex"))
    metadata["participant_unchanged"] = manifest(participant) == manifest(run_participant) == before
    metadata["submitted_files"] = [str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()]
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=int, choices=(1, 2, 3))
    parser.add_argument("generation", type=int, choices=(1, 2, 3, 4))
    parser.add_argument("--attempt-number", type=int)
    arguments = parser.parse_args()
    launch(arguments.concept, arguments.generation, arguments.attempt_number)
