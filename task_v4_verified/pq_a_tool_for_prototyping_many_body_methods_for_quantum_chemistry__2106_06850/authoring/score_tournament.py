import argparse
import concurrent.futures
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from freeze import freeze


ROOT = Path(__file__).resolve().parents[1]
PLANNER_LOCK = threading.Lock()


def artifact_path(directory, concept):
    expected = directory / "submission.json"
    if expected.exists():
        return expected
    if concept == "concept_2":
        candidates = []
        for path in directory.glob("*.json"):
            if path.is_symlink() or path.stat().st_size > 65536:
                continue
            try:
                data = json.loads(path.read_text())
                if isinstance(data, dict) and set(data) == {"schema_version", "orbital_energies", "pair_matrix", "amplitudes"}:
                    candidates.append(path)
            except (ValueError, UnicodeError):
                pass
        if len(candidates) == 1:
            return candidates[0]
    return expected


def score(concept, label):
    base = ROOT / concept
    source = base / "attempts" / label
    frozen = base / "attempts" / (label + "_frozen")
    score_path = base / "attempts" / (label + ".score.json")
    if not frozen.exists():
        freeze(source, frozen)
    launch_manifest = json.loads((base / "attempts" / (label + ".launch.json")).read_text())
    packet = Path(launch_manifest.get("packet", base))
    evaluator = packet / "evaluator/evaluate.py"
    if concept == "concept_1":
        command = [sys.executable, str(evaluator), "--submission", str(frozen), "--report", str(score_path)]
    elif concept == "concept_2":
        command = [sys.executable, "-I", str(evaluator), str(artifact_path(frozen, concept)),
                   "--submission-dir", str(frozen), "--output", str(score_path)]
    else:
        command = [sys.executable, "-I", str(evaluator), "--submission", str(artifact_path(frozen, concept)),
                   "--output", str(score_path)]
    lock = PLANNER_LOCK if concept == "concept_1" else threading.Lock()
    with lock:
        with (base / "attempts" / (label + ".evaluation.log")).open("w") as log:
            process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=7200, check=False)
    if not score_path.is_file():
        raise RuntimeError("no score report: " + concept + "/" + label + ", exit " + str(process.returncode))
    report = json.loads(score_path.read_text())
    summary = {"concept": concept, "attempt": label,
               "passed": report.get("passed", report.get("pass", False)),
               "core_score": report.get("core_score", report.get("core", 0)),
               "worst_score": report.get("worst_family_score", report.get("worst_fidelity")),
               "reason": report.get("reason"), "score_file": str(score_path.relative_to(ROOT)),
               "exit_code": process.returncode}
    print(json.dumps(summary), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, default=1)
    parser.add_argument("--concept", action="append", choices=["concept_1", "concept_2", "concept_3"])
    args = parser.parse_args()
    concepts = args.concept or ["concept_1", "concept_2", "concept_3"]
    label = "v_" + str(args.generation)
    expected = [(concept, attempt) for concept in concepts for attempt in (label, label + "_r2")]
    result_name = "tournament_scores.json" if args.generation == 1 and not args.concept else "tournament_scores_g" + str(args.generation) + "_" + "_".join(concepts) + ".json"
    pending = set(expected)
    futures = {}
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        while pending or futures:
            for concept, label in sorted(pending):
                directory = ROOT / concept / "attempts"
                if (directory / (label + ".exit.json")).is_file():
                    futures[pool.submit(score, concept, label)] = (concept, label)
                    pending.remove((concept, label))
            for future in list(futures):
                if future.done():
                    concept, label = futures.pop(future)
                    try:
                        results.append(future.result())
                    except Exception as error:
                        results.append({"concept": concept, "attempt": label, "infrastructure_error": str(error)})
                        print(json.dumps(results[-1]), flush=True)
                    (ROOT / "authoring" / result_name).write_text(json.dumps(results, indent=2) + "\n")
            if pending or futures:
                time.sleep(10)


if __name__ == "__main__":
    main()
