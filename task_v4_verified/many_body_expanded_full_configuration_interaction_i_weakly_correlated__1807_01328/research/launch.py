import argparse
import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parents[1] / "run_allowlisted_codex.sh"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--packet", type=Path)
    arguments = parser.parse_args()
    attempt = arguments.attempt if arguments.attempt is not None else arguments.generation
    if attempt < 1 or arguments.generation < 1:
        raise ValueError("attempt and generation must be positive")
    concept = ROOT / arguments.concept
    packet = arguments.packet.resolve() if arguments.packet else concept
    participant = packet / "participant"
    if any(path.is_symlink() for path in participant.rglob("*")):
        raise RuntimeError("participant assets must not contain symlinks")
    output = concept / "attempts" / f"v_{attempt}"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("fresh output is not empty")
    for required in (participant / "TASK.md", packet / "evaluator/evaluate.py"):
        if not required.is_file():
            raise RuntimeError(f"missing {required}")
    prompt = ("Read TASK.md and the supplied participant assets. Complete the participant task "
              "autonomously within one hour. Use only the supplied assets and allowed system runtime. "
              f"Write final artifacts and all scratch work into {output}. "
              "The participant directory is read-only. Follow the executable/artifact interface in TASK.md. "
              "Do not access siblings, private data, other attempts or network. "
              "Before substantial work, confirm your output directory is writable, numpy/scipy import, "
              "and the participant assets are readable. Hidden evaluator artifacts are intentionally unavailable.")
    command = ["timeout", "--signal=TERM", "--kill-after=20", "3600", str(RUNNER),
               "--model", "ultima-alpha", "--effort", "xhigh", "--task-read-only",
               str(participant), str(output), prompt]
    prefix = concept / "attempts" / f"v_{attempt}"
    manifest = {"model": "ultima-alpha", "effort": "xhigh", "limit_seconds": 3600,
                "generation": arguments.generation, "attempt": attempt, "command": command,
                "participant": str(participant), "output": str(output),
                "output_initially_empty": True, "ephemeral": True,
                "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "packet": str(packet), "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
                "private_evaluator_sha256_at_launch": {
                    str(path.relative_to(packet / "evaluator")): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted((packet / "evaluator").rglob("*"))
                    if path.is_file() and "__pycache__" not in path.parts},
                "participant_sha256": {str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in sorted(participant.rglob("*")) if path.is_file()}}
    prefix.with_suffix(".launch.json").write_text(json.dumps(manifest, indent=2) + "\n")
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                       MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    with prefix.with_suffix(".session.log").open("w") as logfile:
        process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=logfile, stderr=subprocess.STDOUT, env=environment)
    result = {"returncode": process.returncode, "timed_out": process.returncode in (124, 137),
              "wall_seconds": time.monotonic() - started,
              "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "artifacts": [str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()]}
    prefix.with_suffix(".exit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
