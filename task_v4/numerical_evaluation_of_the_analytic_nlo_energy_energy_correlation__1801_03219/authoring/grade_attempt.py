import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from static_artifact import read_regular


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {"concept_1": "model.json", "concept_2": "witness.json", "concept_3": "design.json"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", choices=sorted(ARTIFACTS))
    parser.add_argument("attempt", type=int)
    arguments = parser.parse_args()
    concept = ROOT / arguments.concept
    basename = f"v_{arguments.attempt}"
    run = json.loads((concept / "attempts" / (basename+".run.json")).read_text())
    if run["status"] != "finished" or run["model"] != "ultima-alpha":
        raise ValueError("only completed runs of the requested model can be graded")
    if not run["participant_unchanged"]:
        raise ValueError("participant files changed during attempt")
    submission = concept / "attempts" / basename
    artifact = submission / ARTIFACTS[arguments.concept]
    deadline_receipt = None
    if run.get("timed_out"):
        deadline_directory = concept / "attempts" / (basename+"_deadline")
        for retry in range(100):
            try:
                deadline_receipt = json.loads((deadline_directory/"capture.json").read_text())
                break
            except (OSError, json.JSONDecodeError):
                time.sleep(0.1)
        if deadline_receipt is None:
            raise ValueError("deadline capture receipt is unavailable")
        captured = deadline_receipt.get("captured_utc_timestamp")
        if captured is not None and captured > deadline_receipt["deadline_utc_timestamp"]:
            raise ValueError("late deadline snapshot")
        artifact = deadline_directory / ARTIFACTS[arguments.concept]
    frozen = concept / "attempts" / (basename+"_frozen")
    frozen.mkdir(exist_ok=False)
    if artifact.is_file() and not artifact.is_symlink():
        contents,unused_stat = read_regular(artifact)
        observed = hashlib.sha256(contents).hexdigest()
        expected = deadline_receipt["sha256"] if deadline_receipt else run["submission_sha256"].get(artifact.name)
        if observed != expected:
            raise ValueError("artifact changed after the run ended")
        (frozen / artifact.name).write_bytes(contents)
    report_path = concept / "attempts" / (basename+".score.json")
    result = subprocess.run([sys.executable, str(concept/"evaluator"/"evaluate.py"),
                             str(frozen), "--report", str(report_path)],
                            capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    print(result.stdout)


if __name__ == "__main__":
    main()
