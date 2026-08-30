import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
ATTEMPTS = [("concept_1",2),("concept_2",1),("concept_2",2),("concept_3",1),("concept_3",2)]


def main():
    completed = set()
    failures = set()
    started = time.monotonic()
    while len(completed) < len(ATTEMPTS) and time.monotonic()-started < 5400:
        for concept,attempt in ATTEMPTS:
            identity = (concept,attempt)
            if identity in completed or identity in failures:
                continue
            base = ROOT/concept/"attempts"/f"v_{attempt}"
            try:
                record = json.loads(base.with_suffix(".run.json").read_text())
            except (OSError,json.JSONDecodeError):
                continue
            if record.get("status") != "finished":
                continue
            score_path = base.with_suffix(".score.json")
            if not score_path.exists():
                result = subprocess.run([sys.executable,str(ROOT/"authoring/grade_attempt.py"),concept,str(attempt)],capture_output=True,text=True,timeout=660)
                base.with_suffix(".grade.log").write_text(result.stdout+result.stderr)
                if result.returncode:
                    failures.add(identity)
                    print(json.dumps({"concept":concept,"attempt":attempt,"grading_error":result.stderr[-1500:]}),flush=True)
                    continue
            score = json.loads(score_path.read_text())
            summary = {"concept":concept,"attempt":attempt,"elapsed_seconds":record.get("elapsed_seconds"),"timed_out":record.get("timed_out")}
            summary.update({key:score.get(key) for key in ["core_score","worst_family_score","max_tolerance_ratio","matched_lags","passed","valid","reason"]})
            print(json.dumps(summary),flush=True)
            completed.add(identity)
        if failures:
            raise RuntimeError(f"manual grading review needed: {failures}")
        if len(completed) < len(ATTEMPTS):
            time.sleep(20)
    if len(completed) != len(ATTEMPTS):
        raise TimeoutError("tournament watch exceeded its orchestration limit")


if __name__ == "__main__":
    main()
