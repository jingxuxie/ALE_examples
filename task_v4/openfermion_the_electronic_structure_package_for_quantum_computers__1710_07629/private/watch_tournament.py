import datetime
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [(1, 1), (2, 1), (2, 2), (3, 1)]


def main():
    finished = set()
    started = time.monotonic()
    while len(finished) != len(EXPECTED):
        for concept_index, attempt_index in EXPECTED:
            key = (concept_index, attempt_index)
            if key in finished:
                continue
            concept = ROOT / f"concept_{concept_index}"
            stem = concept / "attempts" / f"v_{attempt_index}"
            launch_path = Path(str(stem) + ".launch.json")
            if not launch_path.exists():
                continue
            try:
                launch = json.loads(launch_path.read_text())
            except json.JSONDecodeError:
                continue
            if "finished_utc" not in launch:
                continue
            submission = stem
            if concept_index == 2:
                cutoff_path = Path(str(stem) + ".cutoff.json")
                if not cutoff_path.exists():
                    continue
                cutoff = json.loads(cutoff_path.read_text())
                if not cutoff.get("complete"):
                    continue
                submission = Path(cutoff["artifact_directory"])
            report_path = Path(str(stem) + ".evaluation.json")
            if not report_path.exists():
                command = ["/usr/bin/python3", str(ROOT / "private/affinity.py"), str(concept / "evaluator/evaluate.py"), str(submission), "--report", str(report_path)]
                environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
                with Path(str(stem) + ".evaluator.log").open("wb") as logfile:
                    process = subprocess.run(command, env=environment, stdout=logfile, stderr=subprocess.STDOUT, timeout=240)
                if not report_path.exists():
                    raise RuntimeError(f"evaluator produced no report for {key}: {process.returncode}")
            report = json.loads(report_path.read_text())
            summary = {"concept": concept_index, "attempt": attempt_index, "evaluated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "report": str(report_path), "core_score": report.get("core_score"), "worst_family_score": report.get("worst_family_score"), "valid": report.get("valid"), "passed": report.get("passed"), "reason": report.get("reason")}
            print(json.dumps(summary), flush=True)
            finished.add(key)
        if time.monotonic() - started > 7500:
            raise TimeoutError("initial tournament did not terminate within two hours")
        if len(finished) != len(EXPECTED):
            time.sleep(10)


if __name__ == "__main__":
    main()
