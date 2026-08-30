import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def sha256_manifest(directory):
    manifest = {}
    for path in sorted(directory.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            manifest[str(path.relative_to(directory))] = "symlink:" + os.readlink(path)
        elif path.is_file():
            manifest[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def run(concept_name, attempt_name):
    concept = ROOT / concept_name
    participant = concept / "participant"
    for required in (participant / "TASK.md", participant / "input" / "FORMAT.md",
                     concept / "evaluator" / "evaluate.py", concept / "status.json"):
        if not required.is_file():
            raise RuntimeError("Incomplete participant/evaluator package: " + str(required))
    if any(path.is_symlink() for path in participant.rglob("*")):
        raise RuntimeError("Participant assets must not contain symlinks")
    output = concept / "attempts" / attempt_name
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("Fresh-agent output must be empty: " + str(output))
    logs = ROOT / "authoring" / "runs" / concept_name / attempt_name
    logs.mkdir(parents=True, exist_ok=False)
    canary = ROOT / "authoring" / "private_isolation_canary.txt"
    if not canary.exists():
        canary.write_text(os.urandom(32).hex() + "\n")
    home_canary = str(canary).replace("/srv/home/", "/home/", 1)
    aliases = [home_canary, home_canary.replace("/home/", "/srv/home/", 1)]
    prompt = (
        "You are an isolated fresh participant, not the task author. Solve the mission in TASK.md. "
        f"You may read only this participant directory and write your final submission under {output}. "
        "The output starts empty. Do not ask the author for help. You have at most 3600 seconds. "
        "Only assets here are available; no internet or privileged artifacts are permitted. "
        "Before solving, use an ordinary file-open probe on these private canary paths: "
        + repr(aliases) + ". They MUST both be unreadable. Record only the denial/error class "
        "in isolation.json in your output. If either can be read, stop immediately and report isolation failure. "
        "Do not attempt to escape the sandbox. "
        "Put the executable/artifact specified by TASK.md at the top level of your output directory. "
        "Use the provided public examples to check your work."
    )
    command = ["bash", str(RUNNER), "--model", "ultima-alpha", "--effort", "high",
               "--task-read-only", str(participant), str(output), prompt]
    metadata = {
        "model": "ultima-alpha", "reasoning_effort": "high", "time_limit_seconds": 3600,
        "concept": concept_name, "attempt": attempt_name, "participant_access": "read-only",
        "output_initially_empty": True, "participant_manifest": sha256_manifest(participant),
        "started_unix": time.time(), "command": command,
        "evaluator_manifest": sha256_manifest(concept / "evaluator"),
        "discovery_protocol_sha256": hashlib.sha256((ROOT / "authoring/protocol.json").read_bytes()).hexdigest(),
        "status_at_launch": json.loads((concept / "status.json").read_text()),
    }
    (logs / "launch.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (logs / "prompt.txt").write_text(prompt + "\n")
    started = time.monotonic()
    timed_out = False
    cancelled = False
    with (logs / "transcript.log").open("w") as transcript:
        process = subprocess.Popen(command, cwd=participant, stdin=subprocess.DEVNULL,
                                   stdout=transcript, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        while process.poll() is None:
            cancelled = (logs / "CANCEL").exists()
            timed_out = time.monotonic() - started >= 3600
            if cancelled or timed_out:
                break
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
        else:
            returncode = process.returncode
    frozen = logs / "frozen_submission"
    shutil.copytree(output, frozen, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
    result = dict(metadata, returncode=returncode, timed_out=timed_out, cancelled=cancelled,
                  elapsed_seconds=time.monotonic() - started, finished_unix=time.time(),
                  submission_manifest=sha256_manifest(frozen), frozen_submission=str(frozen),
                  participant_unchanged=sha256_manifest(participant) == metadata["participant_manifest"])
    (logs / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("concept", "attempt", "returncode", "timed_out",
                                                "elapsed_seconds", "participant_unchanged")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("attempt")
    arguments = parser.parse_args()
    run(arguments.concept, arguments.attempt)
