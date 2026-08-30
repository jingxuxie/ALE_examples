import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def summarize(result):
    return {key: result.get(key) for key in ["core_score", "worst_family_score", "worst_case_score", "passed", "valid", "reason"] if key in result}


def score(concept, name, artifact=None):
    directory = ROOT / concept
    attempt = directory / "attempts" / name
    record = json.loads((directory / "attempts" / (name + ".run.json")).read_text())
    if record["status"] == "running":
        raise ValueError("cannot score an active attempt")
    result_path = directory / "attempts" / (name + ".evaluation.json")
    if result_path.exists():
        return json.loads(result_path.read_text())
    current = json.loads((directory / "status.json").read_text())
    current_generation = current.get("current_generation", current.get("generation", 1))
    evaluator_directory = directory / "evaluator"
    if record["generation"] != current_generation:
        archive = directory / "generations" / f"generation_{record['generation']}"
        evaluator_directory = archive / ("tested_evaluator" if (archive / "tested_evaluator").exists() else "evaluator")
    evaluator = evaluator_directory / "evaluate.py"
    if concept == "concept_1":
        command = ["/usr/bin/python3", "-B", str(evaluator), str(attempt), "--output", str(result_path)]
        submission = attempt / "solve.py"
    else:
        submission = attempt / (artifact or ("submission.json" if concept == "concept_2" else "control.json"))
        flag = "--submission" if concept == "concept_2" else "--artifact"
        command = ["/usr/bin/python3", "-I", "-B", str(evaluator), flag, str(submission), "--output", str(result_path)]
    before = hashlib.sha256(submission.read_bytes()).hexdigest() if submission.is_file() else None
    recorded = record.get("submission_sha256", {}).get(str(submission.relative_to(attempt)))
    if before != recorded:
        raise RuntimeError(f"artifact differs from the trial-termination manifest: {submission}")
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    watchdog_seconds = 1800 if concept == "concept_3" else 900
    if concept == "concept_2":
        protocol = json.loads((evaluator_directory / "hidden" / "protocol.json").read_text())
        watchdog_seconds = max(watchdog_seconds, protocol["resources"]["evaluation_wall_seconds"] + 180)
    log_path = directory / "attempts" / (name + ".evaluation.log")
    with log_path.open("w") as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment, timeout=watchdog_seconds)
    if not result_path.exists():
        raise RuntimeError(f"evaluator did not produce JSON: {concept}/{name}; see {log_path}")
    result = json.loads(result_path.read_text())
    after = hashlib.sha256(submission.read_bytes()).hexdigest() if submission.is_file() else None
    metadata = {"command": command, "returncode": process.returncode, "artifact": str(submission.relative_to(ROOT)), "artifact_sha256": after, "artifact_unchanged_during_evaluation": before == after, "evaluator_sha256": hashlib.sha256(evaluator.read_bytes()).hexdigest(), "summary": summarize(result)}
    metadata.update({"artifact_matches_cutoff_manifest": before == recorded, "outer_watchdog_seconds": watchdog_seconds})
    (directory / "attempts" / (name + ".scoring.json")).write_text(json.dumps(metadata, indent=2) + "\n")
    if before != after:
        raise RuntimeError("submission changed during evaluation")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--concept")
    parser.add_argument("--attempt")
    parser.add_argument("--artifact")
    parser.add_argument("--workers", type=int, choices=[1, 2], default=1)
    arguments = parser.parse_args()
    if arguments.concept and arguments.attempt:
        print(json.dumps(summarize(score(arguments.concept, arguments.attempt, arguments.artifact)), indent=2), flush=True)
        return
    while True:
        active = False
        ready = []
        records = sorted(ROOT.glob("concept_*/attempts/v_*.run.json"))
        for record_path in records:
            record = json.loads(record_path.read_text())
            if record["status"] == "running":
                active = True
                continue
            name = record_path.name.removesuffix(".run.json")
            result_path = record_path.parent / (name + ".evaluation.json")
            if not result_path.exists():
                concept = record_path.parents[1].name
                ready.append((concept, name))
        if ready:
            with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
                futures = {executor.submit(score, concept, name): (concept, name) for concept, name in ready}
                for future in as_completed(futures):
                    concept, name = futures[future]
                    result = future.result()
                    print(json.dumps({"concept": concept, "attempt": name, **summarize(result)}), flush=True)
        if not arguments.wait or not active:
            break
        time.sleep(15)


if __name__ == "__main__":
    main()
