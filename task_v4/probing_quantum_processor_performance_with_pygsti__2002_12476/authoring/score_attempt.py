import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from run_fresh import ROOT, hashes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept")
    parser.add_argument("--attempt", default="v_1")
    args = parser.parse_args()
    concept = ROOT / args.concept
    record = json.loads((concept / "attempts" / (args.attempt + ".run.json")).read_text())
    assets = ROOT / record["snapshot_root"] if "snapshot_root" in record else concept
    if record["status"] != "finished":
        raise ValueError("cannot grade a live fresh attempt")
    if hashes(assets / "participant") != record["participant_sha256"]:
        raise ValueError("participant artifacts changed during or after the attempt")
    if hashes(assets / "evaluator") != record["evaluator_sha256"]:
        raise ValueError("evaluator artifacts changed during or after the attempt")
    output = concept / "attempts" / args.attempt
    if hashes(output) != record["submission_sha256"]:
        raise ValueError("submission changed after the attempt ended")
    score_path = concept / "attempts" / (args.attempt + ".score.json")
    filenames = {"concept_1": "design.json", "concept_2": "witness.json", "concept_3": "predictions.json"}
    artifact = output / filenames[args.concept]
    command = [sys.executable, str(assets / "evaluator/evaluate.py"), "--submission", str(artifact),
               "--output", str(score_path)]
    if artifact.exists() and (artifact.is_symlink() or not stat.S_ISREG(artifact.lstat().st_mode)):
        score_path.write_text(json.dumps(dict(core_score=0., worst_family_score=0., runtime_seconds=0.,
            passed=False, valid=False, reason="submission must be a self-contained regular JSON artifact"), indent=2) + "\n")
    else:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180,
                                   env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                                            PYTHONDONTWRITEBYTECODE="1"))
        if completed.returncode != 0 and not score_path.exists():
            raise RuntimeError("evaluator failed: " + completed.stderr[-3000:])
    score = json.loads(score_path.read_text())
    receipt = dict(graded_at=datetime.now(timezone.utc).isoformat(), model=record["model"],
                   elapsed_seconds=record["elapsed_seconds"], timed_out=record["timed_out"],
                   participant_unchanged=True, evaluator_unchanged=True, submission_unchanged=True,
                   score_sha256=hashlib.sha256(score_path.read_bytes()).hexdigest(),
                   attempt=args.attempt, core_score=score["core_score"],
                   worst_family_score=score["worst_family_score"], passed=score["passed"],
                   valid=score["valid"], reason=score["reason"])
    (concept / "attempts" / (args.attempt + ".grading.json")).write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
