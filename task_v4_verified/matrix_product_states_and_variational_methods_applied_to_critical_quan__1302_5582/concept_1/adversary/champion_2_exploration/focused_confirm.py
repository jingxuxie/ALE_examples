import concurrent.futures
import json
import time

from harness import ROOT, launch, write_json
from focused_summary import summarize


def main():
    started = time.process_time()
    summary = summarize()
    selected = sorted((entry for entry in summary["cases"] if entry.get("above_screen")),
                      key=lambda entry: entry["v4_energy_gap"], reverse=True)
    jobs = []
    for entry in selected:
        case = entry["case_id"]
        jobs.append((case, "teacher", 80, ROOT / "runs" / case / "v3_40/state.npz", None))
        jobs.append((case, "v4", 40, None, "repeat_v4_40"))
    unfinished = []
    while jobs:
        summary = summarize()
        baseline_parent = json.loads((ROOT / "tranche_2/BATCH_ACCOUNTING.json").read_text())["parent_cpu_seconds"]
        available = 1200 - 40 - summary["recorded_cpu_seconds"] - baseline_parent - time.process_time() + started
        batch = []
        while jobs and len(batch) < 2 and available >= jobs[0][2] + 8:
            job = jobs.pop(0)
            batch.append(job)
            available -= job[2] + 8
        if not batch:
            unfinished = jobs
            break
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = [pool.submit(launch, *job) for job in batch]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        summary = summarize()
        print(json.dumps({"checkpoint": True, "recorded_cpu_seconds": summary["recorded_cpu_seconds"],
                          "positive_cases": summary["positive_cases"]}), flush=True)
    write_json(ROOT / "tranche_2/CONFIRM_ACCOUNTING.json", {
        "parent_cpu_seconds": time.process_time() - started,
        "unfinished_jobs": [[str(value) if value is not None else None for value in job] for job in unfinished],
        "recorded_solver_cpu_seconds": summarize()["recorded_cpu_seconds"]})


if __name__ == "__main__":
    main()
