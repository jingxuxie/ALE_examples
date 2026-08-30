import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import sys
import time


for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import run_episode


def initialize_worker():
    processors = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {processors[os.getpid() % len(processors)]})


def run_job(job):
    submission, case, outcome_seed, config = job
    episode = {"id": case["id"], "family": case["family"], "parameters": case["parameters"], "outcome_seed": outcome_seed}
    result = run_episode(Path(submission), episode, config)
    result["screening_seed"] = outcome_seed
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--pool", type=Path, default=ROOT / "adversary/stress_pool.json")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--replicas", type=int, default=3)
    args = parser.parse_args()
    pool = json.loads(args.pool.read_text())
    config = json.loads((ROOT / "evaluator/config.json").read_text())
    jobs = [(str(args.submission.resolve()), case, seed, config)
            for case in pool["cases"] for seed in case["screening_seeds"][:args.replicas]]
    results = []
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize_worker) as executor:
        futures = [executor.submit(run_job, job) for job in jobs]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            grouped = {}
            for row in results:
                grouped.setdefault(row["id"], []).append(row)
            cases = [{"id": identifier, "family": rows[0]["family"], "replicas": len(rows),
                      "mean_score": sum(row["score"] for row in rows) / len(rows),
                      "worst_score": min(row["score"] for row in rows),
                      "all_valid": all(row["valid"] for row in rows),
                      "mean_parameter_loss": sum(row.get("parameter_loss", 0) for row in rows) / len(rows),
                      "mean_predictive_rmse": sum(row.get("predictive_rmse", 0) for row in rows) / len(rows)}
                     for identifier, rows in grouped.items()]
            report = {"kind": "private repeated-outcome stress search, not a fresh-agent attempt",
                      "submission": str(args.submission), "completed_episodes": len(results),
                      "requested_episodes": len(jobs), "elapsed_seconds": time.monotonic() - started,
                      "cases": sorted(cases, key=lambda item: item["id"]), "episodes": results}
            args.output.write_text(json.dumps(report, indent=2))
            print(result["id"], round(result["score"], 5), result["valid"], flush=True)


if __name__ == "__main__":
    main()
