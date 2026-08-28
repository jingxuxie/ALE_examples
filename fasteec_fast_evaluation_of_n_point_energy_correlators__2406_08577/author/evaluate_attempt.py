import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--kind", required=True)
parser.add_argument("--version", default="pilot")
parser.add_argument("--split", default="pilot")
parser.add_argument("--case")
arguments = parser.parse_args()
concept = root / "pilots" / arguments.kind if arguments.version == "pilot" else root / "ratchets" / arguments.kind / arguments.version
private = concept / "private"
submission = concept / "attempt" / "solve.py"
run = json.loads((root / "author" / "runs" / (arguments.kind + "_" + arguments.version + ".json")).read_text())
if not run["submission_exists"]:
    raise RuntimeError("No submission; record as an incomplete attempt, not a numerical result")
deadline = time.monotonic() + 7200
while True:
    manifest = json.loads((private / "challenge_pool" / "manifest.json").read_text())
    cases = [case for case in manifest["cases"] if case["split"] == arguments.split and (not arguments.case or arguments.case == case["id"])]
    complete = bool(cases)
    if arguments.version == "pilot" and arguments.split == "pilot" and not arguments.case:
        complete = complete and any(case["id"] == "pilot_full_sample_scale" for case in cases)
    for case in cases:
        try:
            record = json.loads((private / "reference" / (case["id"] + ".json")).read_text())
            complete = complete and bool(record["histograms"])
        except (OSError, ValueError):
            complete = False
    if complete:
        break
    if time.monotonic() >= deadline:
        raise RuntimeError("Private references did not finish in two hours")
    time.sleep(5)
shutil.copyfile(root / "author" / "evaluator_template.py", private / "evaluator.py")
report_dir = root / "author" / "reports"
report_dir.mkdir(exist_ok=True)
label = arguments.kind + "_" + arguments.version + ("_" + arguments.split if arguments.split != "pilot" else "") + ("_" + arguments.case if arguments.case else "")
before = hashlib.sha256(submission.read_bytes()).hexdigest()
command = [sys.executable, str(private / "evaluator.py"), "--solver", str(submission), "--split", arguments.split, "--report", str(report_dir / (label + ".json"))]
if arguments.case:
    command += ["--case", arguments.case]
with (root / "author" / "benchmark.lock").open("w") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    subprocess.run(command, check=True)
after = hashlib.sha256(submission.read_bytes()).hexdigest()
if before != after:
    raise RuntimeError("Submission changed during evaluation")
(report_dir / (label + ".audit.json")).write_text(json.dumps({"submission_sha256": before, "runner_model": run["model"], "runner_wall_seconds": run["wall_seconds"], "sandbox": "bubblewrap: network disabled, participant read-only, submission directory writable, private tree absent", "frozen_entrypoint": True}, indent=2))
