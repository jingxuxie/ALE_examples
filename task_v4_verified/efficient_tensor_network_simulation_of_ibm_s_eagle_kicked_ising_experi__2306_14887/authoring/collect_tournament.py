import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent


def file_hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file() and not path.is_symlink()}


def score(concept_number, attempt_number):
    concept = ROOT / f"concept_{concept_number}"
    run = json.loads((concept / "attempts" / f"v_{attempt_number}_run.json").read_text())
    original = concept / "attempts" / f"v_{attempt_number}"
    snapshot = concept / "attempts" / f"frozen_v_{attempt_number}"
    if snapshot.exists():
        raise RuntimeError("refusing to overwrite a frozen submission")
    shutil.copytree(original, snapshot, symlinks=True)
    frozen = {"original": str(original), "snapshot": str(snapshot),
              "copied_after_fresh_process_exit": True, "frozen_at_unix": time.time(),
              "hashes": file_hashes(snapshot)}
    (concept / "attempts" / f"v_{attempt_number}_snapshot.json").write_text(json.dumps(frozen, indent=2) + "\n")
    score_path = concept / "attempts" / f"v_{attempt_number}_score.json"
    command = [sys.executable, "-I", str(concept / "evaluator" / "evaluate.py"),
               "--submission", str(snapshot), "--output", str(score_path)]
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    completed = subprocess.run(command, cwd=concept, env=environment, capture_output=True,
                               text=True, timeout=1500)
    (concept / "attempts" / f"v_{attempt_number}_scoring.log").write_text(completed.stdout + "\n" + completed.stderr)
    if not score_path.is_file():
        raise RuntimeError(f"checker did not write result: {completed.stderr[-1200:]}")
    result = json.loads(score_path.read_text())
    result["concept"] = concept_number
    result["attempt"] = attempt_number
    result["model"] = run["model"]
    result["fresh_elapsed_seconds"] = run["elapsed_seconds"]
    result["fresh_timed_out"] = run["timed_out"]
    result["fresh_returncode"] = run["returncode"]
    result["participant_unchanged"] = run["participant_unchanged"]
    result["submission_files"] = sorted(frozen["hashes"])
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("cases", "families", "submission_files")}), flush=True)
    return result


def main(attempt_number, concepts):
    pending = set(concepts)
    active = {}
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        while pending or active:
            for concept_number in sorted(pending.copy()):
                path = ROOT / f"concept_{concept_number}" / "attempts" / f"v_{attempt_number}_run.json"
                if not path.is_file():
                    continue
                try:
                    metadata = json.loads(path.read_text())
                except json.JSONDecodeError:
                    continue
                if metadata["status"] == "finished":
                    active[executor.submit(score, concept_number, attempt_number)] = concept_number
                    pending.remove(concept_number)
                    print(f"Scoring frozen concept_{concept_number} submission", flush=True)
            for future in list(active):
                if not future.done():
                    continue
                concept_number = active.pop(future)
                try:
                    results[str(concept_number)] = future.result()
                except Exception as error:
                    results[str(concept_number)] = {"infrastructure_error": repr(error)}
                (ROOT / "authoring" / f"tournament_v{attempt_number}.json").write_text(json.dumps(results, indent=2) + "\n")
            if pending or active:
                time.sleep(10)
    print(f"Tournament {attempt_number} collected", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--concepts", type=int, nargs="+", default=[1, 2, 3])
    arguments = parser.parse_args()
    main(arguments.attempt, arguments.concepts)
