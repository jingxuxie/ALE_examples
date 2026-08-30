import concurrent.futures
import json
import time

from harness import ROOT, launch, write_json
from focused_summary import summarize


def main():
    started = time.process_time()
    wall_started = time.monotonic()
    plan = json.loads((ROOT / "tranche_2/PLAN.json").read_text())
    jobs = [(entry["case_id"], solver) for entry in plan["initial_configurations"] for solver in ("v4", "v3")]
    while jobs:
        summary = summarize()
        consumed = summary["recorded_cpu_seconds"] + time.process_time() - started
        available = int((1200 - 30 - consumed) // 48)
        if available < 1:
            break
        batch = jobs[:min(2, available)]
        jobs = jobs[len(batch):]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = [pool.submit(launch, case, solver, 40) for case, solver in batch]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        summary = summarize()
        print(json.dumps({"checkpoint": True, "recorded_cpu_seconds": summary["recorded_cpu_seconds"],
                          "positive_cases": summary["positive_cases"]}), flush=True)
    write_json(ROOT / "tranche_2/BATCH_ACCOUNTING.json", {
        "parent_cpu_seconds": time.process_time() - started,
        "wall_seconds": time.monotonic() - wall_started,
        "unrun_jobs": jobs, "recorded_solver_cpu_seconds": summarize()["recorded_cpu_seconds"]})


if __name__ == "__main__":
    main()
