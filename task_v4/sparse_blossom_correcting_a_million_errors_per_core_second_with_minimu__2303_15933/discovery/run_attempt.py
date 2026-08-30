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


def now():
    return datetime.now(timezone.utc).isoformat()


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        result[str(path.relative_to(directory))] = digest.hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", type=Path)
    parser.add_argument("--attempt", default="v_1")
    parser.add_argument("--seconds", type=int, default=3600)
    parser.add_argument("--model", default="ultima-alpha")
    parser.add_argument("--effort", default="high")
    args = parser.parse_args()
    concept = args.concept.resolve()
    participant = concept / "participant"
    output = concept / "attempts" / args.attempt
    logs = concept / "attempts" / (args.attempt + "_logs")
    if not (participant / "TASK.md").is_file():
        raise ValueError("participant TASK.md missing")
    if output.exists() and any(output.iterdir()):
        raise ValueError("fresh output directory is not empty")
    output.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=False)
    freeze = {
        "timestamp": now(),
        "model": args.model,
        "effort": args.effort,
        "limit_seconds": args.seconds,
        "output_empty_at_launch": True,
        "participant_sha256": inventory(participant),
        "evaluator_sha256": inventory(concept / "evaluator"),
        "status_at_launch": json.loads((concept / "status.json").read_text()),
    }
    (logs / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    prompt = (
        f"Read TASK.md and the provided participant assets, then solve the task independently. "
        f"Write your complete runnable submission into {output}. "
        f"You have up to {args.seconds} seconds. The participant tree is read-only; "
        f"use the output directory for all code, experiments, temporary files and final artifacts. "
        "Only the participant assets and your own output are available. Follow the executable "
        "interface and resource constraints in the task. Do not stop at a proposal: produce "
        "the best working submission you can and test it using the provided assets."
    )
    command = [str(RUNNER), "--model", args.model, "--effort", args.effort,
               "--task-read-only", str(participant), str(output), prompt]
    metadata = {"started": now(), "command": command, "isolation": "provided allowlist runner",
                "network": "disabled", "fresh_ephemeral": True}
    (logs / "launch.json").write_text(json.dumps(metadata, indent=2) + "\n")
    start = time.monotonic()
    with (logs / "stdout.log").open("wb") as stdout, (logs / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
        timed_out = False
        try:
            returncode = process.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                returncode = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
    metadata.update({"finished": now(), "elapsed_seconds": time.monotonic() - start,
                     "returncode": returncode, "timed_out": timed_out,
                     "submission_sha256": inventory(output),
                     "participant_unchanged": inventory(participant) == freeze["participant_sha256"]})
    (logs / "launch.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({key: value for key, value in metadata.items() if key != "submission_sha256"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
