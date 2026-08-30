import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concept", choices=["concept_1", "concept_2", "concept_3"])
    parser.add_argument("--attempt", type=int, default=1)
    arguments = parser.parse_args()
    metadata = ROOT / arguments.concept / "attempts" / f"v_{arguments.attempt}.metadata.json"
    while True:
        try:
            record = json.loads(metadata.read_text())
        except (OSError, json.JSONDecodeError):
            time.sleep(5)
            continue
        if "finished_utc" in record:
            break
        deadline = datetime.datetime.fromisoformat(record["deadline_utc"])
        if datetime.datetime.now(datetime.timezone.utc) > deadline + datetime.timedelta(minutes=2):
            raise RuntimeError("Attempt supervisor did not finish after its deadline")
        time.sleep(5)
    command = ["python", str(ROOT / "research" / "score_attempt.py"), arguments.concept,
               "--attempt", str(arguments.attempt)]
    subprocess.run(command, check=True, env=dict(os.environ, OPENBLAS_NUM_THREADS="1",
                   OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1"))


if __name__ == "__main__":
    main()
