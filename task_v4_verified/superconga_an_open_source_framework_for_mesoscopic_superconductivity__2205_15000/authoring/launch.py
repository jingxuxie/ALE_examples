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
    if not (participant / "TASK.md").is_file() or not (packet / "evaluator" / "evaluate.py").is_file():
        raise RuntimeError("packet is missing participant or evaluator")
    label = "v_" + str(arguments.generation)
    if arguments.replicate > 1:
        label += "_r" + str(arguments.replicate)
    output = concept / "attempts" / label
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("fresh-agent output directory is not empty")
    prefix = concept / "attempts" / label
    prompt = ("Read TASK.md and the supplied assets in your working directory. "
              "Complete the participant task autonomously within one hour. "
              "Use only the provided participant assets and allowed system runtime. "
              "Write all final artifacts to " + str(output) + ". "
              "The participant directory is read-only; put experiments and scratch "
              "in your output directory or temporary storage. The evaluator will "
              "use the executable/artifact contract in TASK.md. Do not access other "
              "tasks, private data, or sibling attempts; external network is disabled.")
    command = ["timeout", "--signal=TERM", "--kill-after=20", "3600",
               str(RUNNER), "--model", "ultima-alpha", "--effort", "xhigh",
               "--task-read-only", str(participant), str(output), prompt]
    manifest = {"model": "ultima-alpha", "effort": "xhigh", "limit_seconds": 3600,
                "generation": arguments.generation, "replicate": arguments.replicate, "command": command,
                "participant": str(participant), "output": str(output),
                "packet": str(packet),
                "output_initially_empty": True, "ephemeral": True,
                "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "participant_sha256": {str(path.relative_to(participant)): hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in sorted(participant.rglob("*")) if path.is_file()}}
    prefix.with_suffix(".launch.json").write_text(json.dumps(manifest, indent=2) + "\n")
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    started = time.monotonic()
    with prefix.with_suffix(".session.log").open("w") as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
    finish = {"returncode": process.returncode, "timed_out": process.returncode in (124, 137),
              "wall_seconds": time.monotonic() - started,
              "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "artifacts": [str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()]}
    prefix.with_suffix(".exit.json").write_text(json.dumps(finish, indent=2) + "\n")
    print(json.dumps(finish, indent=2), flush=True)


if __name__ == "__main__":
    main()
