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
    parser.add_argument("--concept", required=True)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--replicate", type=int, default=1)
    parser.add_argument("--packet", type=Path)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    packet = arguments.packet.resolve() if arguments.packet else concept
    participant = packet / "participant"
    label = "v_" + str(arguments.generation)
    if arguments.replicate > 1:
        label += "_r" + str(arguments.replicate)
    output = concept / "attempts" / label
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("fresh output must be empty")
    if not (participant / "TASK.md").is_file():
        raise RuntimeError("missing task")
    prompt = (
        "Read TASK.md and solve the participant task autonomously within one hour. "
        "Only the participant assets and your empty writable output directory are available. "
        "The participant directory is read-only; put all experiments, scratch and final "
        "artifacts in " + str(output) + ". Follow the executable/artifact interface in TASK.md. "
        "Do not access sibling tasks, attempts, evaluator files, or external network. "
        "You have the full one-hour limit, and may use it to improve and validate your result."
    )
    command = ["timeout", "--signal=TERM", "--kill-after=20", "3600", str(RUNNER),
               "--model", "ultima-alpha", "--effort", "xhigh", "--task-read-only",
               str(participant), str(output), prompt]
    prefix = output.parent / output.name
    manifest = {
        "model": "ultima-alpha", "limit_seconds": 3600, "ephemeral": True,
        "generation": arguments.generation, "replicate": arguments.replicate, "output_initially_empty": True,
        "participant_read_only": True, "packet": str(packet), "command": command,
        "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "participant_sha256": {
            str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(participant.rglob("*")) if path.is_file()
        },
    }
    prefix.with_suffix(".launch.json").write_text(json.dumps(manifest, indent=2) + "\n")
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    started = time.monotonic()
    with prefix.with_suffix(".session.log").open("w") as stream:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, env=environment)
    manifest["returncode"] = result.returncode
    manifest["timed_out"] = result.returncode in (124, 137)
    manifest["wall_seconds"] = time.monotonic() - started
    manifest["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest["artifacts"] = [str(path.relative_to(output)) for path in sorted(output.rglob("*")) if path.is_file()]
    prefix.with_suffix(".exit.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in ("returncode", "timed_out", "wall_seconds", "artifacts")}), flush=True)


if __name__ == "__main__":
    main()
