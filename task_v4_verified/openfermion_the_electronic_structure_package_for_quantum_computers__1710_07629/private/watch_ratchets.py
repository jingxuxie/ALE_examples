import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", action="append", required=True)
    arguments = parser.parse_args()
    pending = {tuple(int(part) for part in item.split(":")) for item in arguments.attempt}
    while pending:
        for concept, attempt in sorted(pending):
            stem = ROOT / f"concept_{concept}/attempts/v_{attempt}"
            launch_path = Path(str(stem) + ".launch.json")
            if not launch_path.exists():
                continue
            try:
                launch = json.loads(launch_path.read_text())
            except json.JSONDecodeError:
                continue
            if "elapsed_seconds" not in launch:
                continue
            if not launch.get("participant_unchanged") or not launch.get("evaluator_unchanged"):
                raise RuntimeError(f"frozen package changed during {stem}")
            if not launch.get("scoring_snapshot"):
                raise RuntimeError(f"missing immutable scoring snapshot for {stem}")
            evaluator = Path(launch["evaluator"]) / "evaluate.py"
            report_path = Path(str(stem) + ".evaluation.json")
            if not report_path.exists():
                command = [sys.executable, str(ROOT / "private/affinity.py"), str(evaluator), launch["scoring_snapshot"], "--report", str(report_path)]
                with Path(str(stem) + ".evaluator.log").open("w") as logfile:
                    subprocess.run(command, stdout=logfile, stderr=subprocess.STDOUT, timeout=360)
            report = json.loads(report_path.read_text())
            progress = {"observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "concept": concept, "attempt": attempt, "generation": str(Path(launch["participant"]).parent.relative_to(ROOT)), "scoring_snapshot": launch["scoring_snapshot"], "core_score": report.get("core_score"), "worst_family_score": report.get("worst_family_score"), "valid": report.get("valid"), "passed": report.get("passed"), "reason": report.get("reason")}
            print(json.dumps(progress), flush=True)
            pending.remove((concept, attempt))
        if pending:
            time.sleep(5)


if __name__ == "__main__":
    main()
