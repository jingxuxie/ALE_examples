"""Score only completed immutable attempts while other fresh agents continue."""

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent


def score(concept, stage):
    concept_dir = ROOT / "concepts" / concept
    participant = concept_dir / "participant" if stage == "pilot" else concept_dir / stage / "participant"
    attempt = concept_dir / "attempt" if stage == "pilot" else concept_dir / stage / "attempt"
    destination = ROOT / "author/scores"
    destination.mkdir(parents=True, exist_ok=True)
    report = destination / f"{concept}_{stage}.json"
    if not (attempt / "solve.py").exists():
        result = {"concept": concept, "stage": stage, "valid_attempt": False,
                  "reason": "No executable submission; this cannot establish scientific hardness."}
        report.write_text(json.dumps(result, indent=2) + "\n")
        return result
    command = [sys.executable, "-B", str(ROOT / "author/score_submission.py"),
               str(concept_dir), str(attempt / "solve.py"), "--split", "all",
               "--participant", str(participant), "--report", str(report)]
    stage_manifest = concept_dir / "private/challenge_pool" / f"{stage}_manifest.json"
    if stage != "pilot" and stage_manifest.exists():
        command.extend(["--manifest", str(stage_manifest)])
    with report.with_suffix(".log").open("w") as stream:
        execution = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL,
                                   env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"))
    result = {"concept": concept, "stage": stage, "returncode": execution.returncode,
              "report": str(report)}
    if execution.returncode == 0:
        result["summary"] = json.loads(report.read_text())["summary"]
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concepts", nargs="+")
    parser.add_argument("--stage", default="pilot")
    args = parser.parse_args()
    remaining = set(args.concepts)
    jobs = []
    deadline = time.monotonic() + 4500
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        while remaining and time.monotonic() < deadline:
            for concept in list(remaining):
                path = ROOT / "author/pilot_logs" / f"{concept}_{args.stage}.json"
                try:
                    evidence = json.loads(path.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                if "finished_utc" not in evidence:
                    continue
                if evidence["participant_sha256_before"] != evidence["participant_sha256_after"]:
                    raise RuntimeError("Read-only participant changed during attempt: " + concept)
                jobs.append(executor.submit(score, concept, args.stage))
                remaining.remove(concept)
            if remaining:
                time.sleep(15)
        results = [job.result() for job in jobs]
    report = {"stage": args.stage, "remaining": sorted(remaining), "results": results}
    (ROOT / "author/scores" / f"{args.stage}_batch.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
