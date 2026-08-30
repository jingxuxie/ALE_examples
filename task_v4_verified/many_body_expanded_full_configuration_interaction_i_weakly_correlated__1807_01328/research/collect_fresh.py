import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOBS = (("concept_1", 2, "adversary/ratchet_1"),
        ("concept_2", 3, "adversary/ratchet_2"),
        ("concept_2", 4, "adversary/ratchet_2"))


def score(job):
    name, attempt, packet_relative = job
    concept = ROOT / name
    packet = concept / packet_relative
    prefix = concept / "attempts" / f"v_{attempt}"
    output = prefix.with_suffix(".score.json")
    command = [sys.executable, "-B", str(packet / "evaluator/evaluate.py")]
    if name == "concept_1":
        command += ["--submission", str(prefix), "--output", str(output)]
    else:
        command += ["--artifact", str(prefix / "witness.json"), "--report", str(output)]
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                       MKL_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    if not output.exists():
        with prefix.with_suffix(".evaluation.log").open("w") as logfile:
            completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=logfile,
                                       stderr=subprocess.STDOUT, env=environment, timeout=700)
        if completed.returncode:
            raise RuntimeError(f"evaluation failed for {name}/v_{attempt}; inspect its evaluation log")
    result = json.loads(output.read_text())
    summary = {key: result.get(key) for key in
               ("valid", "passed", "core_score", "worst_family_score", "rmse_hartree",
                "worst_family_rmse_hartree", "cpu_seconds", "runtime_seconds", "reason", "family_scores")}
    summary.update(concept=name, attempt=attempt, score_file=str(output.relative_to(ROOT)),
                   packet=packet_relative)
    print(json.dumps(summary), flush=True)
    return summary


def main():
    pending = list(JOBS)
    futures = {}
    results = []
    deadline = time.monotonic() + 4500
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        while pending or futures:
            if time.monotonic() > deadline:
                raise TimeoutError("fresh attempt collection deadline")
            for job in list(pending):
                name, attempt, packet_relative = job
                if (ROOT / name / "attempts" / f"v_{attempt}.exit.json").is_file():
                    futures[pool.submit(score, job)] = job
                    pending.remove(job)
            for future in list(futures):
                if future.done():
                    results.append(future.result())
                    del futures[future]
            if pending or futures:
                time.sleep(3)
    report = {"all_scheduled_attempts_evaluated": True,
              "results": sorted(results, key=lambda result: (result["concept"], result["attempt"]))}
    (ROOT / "research/final_tournament_scores.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"collection_complete": True, "attempts": len(results)}), flush=True)


if __name__ == "__main__":
    main()
