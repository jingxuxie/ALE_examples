import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", required=True)
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--replicate", type=int, default=1)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    label = "v_" + str(arguments.generation)
    if arguments.replicate > 1:
        label += "_r" + str(arguments.replicate)
    prefix = concept / "attempts" / label
    launch = json.loads(prefix.with_suffix(".launch.json").read_text())
    start = datetime.datetime.fromisoformat(launch["started_utc"]).timestamp()
    snapshot = prefix.with_suffix(".research_snapshot")
    while not prefix.with_suffix(".exit.json").exists():
        if time.time() > start + launch["limit_seconds"] + 180:
            raise RuntimeError("launcher completion record absent after deadline; infrastructure audit required")
        if arguments.concept == "concept_2":
            for source in prefix.rglob("*.py"):
                try:
                    if source.is_symlink() or source.stat().st_size > 4 * 1024 ** 2:
                        continue
                    destination = snapshot / source.relative_to(prefix)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                except FileNotFoundError:
                    continue
        time.sleep(15)
    changed = []
    participant = Path(launch["participant"])
    for relative, expected in launch["participant_sha256"].items():
        current = participant / relative
        if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != expected:
            changed.append(relative)
    if changed:
        raise RuntimeError("participant changed during the attempt: " + repr(changed))
    report = prefix.with_suffix(".evaluation.json")
    output_flag = "--output" if arguments.concept == "concept_3" else "--report"
    packet = Path(launch.get("packet", concept))
    command = [sys.executable, str(packet / "evaluator" / "evaluate.py"),
               "--submission", str(prefix), output_flag, str(report)]
    environment = os.environ.copy()
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                        "MKL_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    evaluated = subprocess.run(command, env=environment)
    if evaluated.returncode != 0 or not report.exists():
        raise RuntimeError("evaluator invocation failed; no hardness decision")
    record = {"concept": arguments.concept, "generation": arguments.generation,
              "replicate": arguments.replicate,
              "participant_unchanged": True, "command": command,
              "launch_exit": json.loads(prefix.with_suffix(".exit.json").read_text()),
              "report": str(report.relative_to(ROOT)),
              "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    prefix.with_suffix(".audit.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
