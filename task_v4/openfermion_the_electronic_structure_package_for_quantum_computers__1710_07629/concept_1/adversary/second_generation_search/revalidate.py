import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TASK = ROOT.parent
OUTPUT = HERE / "champion_2_revalidation"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUTPUT.mkdir(exist_ok=True)
    started = time.time()
    summary = {
        "started_unix": started,
        "batch_order": [11, 6, 7, 9, 10],
        "original_reports_preserved": True,
        "budget_seconds_per_case": 10,
        "cpu": 188,
        "mutex": str(TASK / "private/evaluation.lock"),
        "batches": [],
    }
    for number in summary["batch_order"]:
        source = HERE / "champion_2_audit" / f"batch_{number:02d}"
        destination = OUTPUT / f"batch_{number:02d}"
        destination.mkdir(exist_ok=True)
        payload = destination / "request.json"
        payload.write_bytes((source / "request.json").read_bytes())
        command = [
            "taskset", "-c", "188", sys.executable,
            str(TASK / "private/affinity.py"),
            str(TASK / "private/capture_gauge_evaluation.py"),
            "--evaluator", str(ROOT / "generations/generation_1/evaluator/evaluate.py"),
            "--submission", str(ROOT / "champions/generation_2"),
            "--cases", str(payload),
            "--report", str(destination / "report.json"),
            "--response", str(destination / "response.json"),
        ]
        original_hash = digest(source / "report.json")
        run_started = time.monotonic()
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        with (destination / "evaluation.log").open("w") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                    env=environment, timeout=180, check=False)
        report_path = destination / "report.json"
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        entry = {
            "batch": number,
            "returncode": result.returncode,
            "queue_inclusive_wall_seconds": time.monotonic() - run_started,
            "request_sha256": digest(payload),
            "matches_original_request": digest(payload) == digest(source / "request.json"),
            "original_report_sha256": original_hash,
            "original_report_unchanged": original_hash == digest(source / "report.json"),
            "command": command,
            "report": report,
        }
        summary["batches"].append(entry)
        summary["elapsed_wall_seconds"] = time.time() - started
        (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({"batch": number, "valid": report.get("valid"),
                          "runtime": report.get("runtime_seconds"),
                          "reason": report.get("reason")}), flush=True)


if __name__ == "__main__":
    main()
