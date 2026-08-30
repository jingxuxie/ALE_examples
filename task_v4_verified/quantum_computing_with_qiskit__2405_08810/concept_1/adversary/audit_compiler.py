import argparse
import collections
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    options = parser.parse_args()
    cases = json.loads(options.cases.read_text())
    destination = options.output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    targets = json.loads((ROOT / "evaluator" / "hidden" / "targets.json").read_text())
    started = time.monotonic()

    def evaluate_batch(batch_index):
        batch = cases[batch_index::options.workers]
        case_path = destination / f"batch_{batch_index}_cases.json"
        score_path = destination / f"batch_{batch_index}_score.json"
        case_path.write_text(json.dumps(batch, separators=(",", ":")) + "\n")
        command = [sys.executable, str(ROOT / "evaluator" / "evaluate.py"), str(options.submission.resolve()), "--cases", str(case_path), "--output", str(score_path)]
        with (destination / f"batch_{batch_index}_stdout.log").open("w") as stdout, (destination / f"batch_{batch_index}_stderr.log").open("w") as stderr:
            process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env=environment, timeout=100 + 15 * len(batch))
        if process.returncode != 0 or not score_path.exists():
            raise RuntimeError(f"evaluator infrastructure failed in batch {batch_index}")
        return json.loads(score_path.read_text())

    with ThreadPoolExecutor(max_workers=options.workers) as executor:
        batches = list(executor.map(evaluate_batch, range(options.workers)))
    results = [result for batch in batches for result in batch["cases"]]
    grouped = collections.defaultdict(list)
    for result in results:
        grouped[result["family"]].append(result["reduction"])
    families = {family: statistics.mean(values) for family, values in grouped.items()}
    valid = all(batch["valid"] for batch in batches) and len(results) == len(cases)
    core = statistics.mean(result["reduction"] for result in results) if valid else 0.0
    worst = min(families.values()) if valid else 0.0
    passed = valid and core >= targets["core_score"] and worst >= targets["worst_family_score"]
    report = {"core_score": core, "worst_family_score": worst, "resource_score": min(batch["resource_score"] for batch in batches), "max_case_seconds": max(batch["max_case_seconds"] for batch in batches), "valid": valid, "passed": passed, "reason": "all fixed targets met" if passed else "fixed target missed" if valid else "one or more cases invalid", "family_scores": families, "targets": targets, "case_count": len(cases), "cases_sha256": hashlib.sha256(options.cases.read_bytes()).hexdigest(), "elapsed_seconds": time.monotonic() - started, "workers": options.workers, "cases": results}
    (destination / "score.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
