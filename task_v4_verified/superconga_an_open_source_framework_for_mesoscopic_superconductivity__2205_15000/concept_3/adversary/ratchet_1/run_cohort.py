import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

import evaluate


def run_case(case, submission, budget, observe_cpu=False):
    if observe_cpu:
        from observed_sandbox import ObservedSandbox
        evaluate.Sandbox = ObservedSandbox
    evaluate.model.SPEC["query_budget"] = budget
    result = evaluate.run_episode(case, ROOT / "champions" / "generation_1" / "participant", submission, "solve.py")
    if observe_cpu:
        result.update(ObservedSandbox.latest.measurement())
    result.update({"cohort": case.get("cohort", "recheck"), "mode": case.get("mode", "recheck"),
                   "case_sha256": hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
                   "features": case.get("features"), "query_budget": budget})
    return result


def report_results(results, elapsed, budget):
    summary = evaluate.aggregate(results, official=False)
    groups = {}
    for key in ("cohort", "mode", "family"):
        groups[key] = {}
        for value in sorted({result[key] for result in results}):
            selection = [result for result in results if result[key] == value]
            groups[key][value] = {"count": len(selection), "successes": sum(result["metrics"]["joint_success"] for result in selection),
                                  "invalid": sum(not result["protocol_valid"] for result in selection),
                                  "mean_cpu_seconds": sum(result["cpu_seconds"] for result in selection) / len(selection)}
    return {"schema": "ratchet-champion-screen-v1", "query_budget": budget, "summary": summary, "groups": groups,
            "screen_wall_seconds": elapsed, "isolation": "unchanged trusted evaluator.run_episode + Sandbox",
            "parallel_cpu_accounting": "one host worker process per concurrent episode; os.times undercounts bwrap descendants on this host; observed runs additionally sample the kernel process tree",
            "failures": [result["case_id"] for result in results if not result["metrics"]["joint_success"]], "episodes": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=HERE / "cases_96.json")
    parser.add_argument("--results", type=Path, default=HERE / "screen_96")
    parser.add_argument("--submission", type=Path, default=HERE / "submission")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--budget", type=int, default=56)
    parser.add_argument("--observe-cpu", action="store_true")
    arguments = parser.parse_args()
    for path in (arguments.cases.resolve(), arguments.results.resolve(), arguments.submission.resolve()):
        if HERE not in path.parents:
            parser.error("all artifacts and staging must remain inside ratchet_1")
    cases = json.loads(arguments.cases.read_text())["episodes"]
    arguments.results.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    results = []
    pending = []
    for case in cases:
        path = arguments.results / (case["id"] + ".json")
        if path.exists():
            result = json.loads(path.read_text())
            expected = hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()
            if result["case_sha256"] != expected or result["query_budget"] != arguments.budget:
                raise ValueError("resume mismatch")
            results.append(result)
        else:
            pending.append(case)
    with ProcessPoolExecutor(max_workers=arguments.workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(run_case, case, arguments.submission.resolve(), arguments.budget, arguments.observe_cpu): case for case in pending}
        for future in as_completed(futures):
            case = futures[future]
            result = future.result()
            (arguments.results / (case["id"] + ".json")).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
            results.append(result)
            print(json.dumps({"completed": len(results), "total": len(cases), "case": case["id"], "valid": result["protocol_valid"],
                              "success": result["metrics"]["joint_success"], "f1": result["metrics"]["support_f1"],
                              "strength_error": result["metrics"]["relative_strength_error"], "vortex_exact": result["metrics"]["vortex_exact"],
                              "cpu": round(result["cpu_seconds"], 3), "wall": round(result["wall_seconds"], 3)}), flush=True)
    results.sort(key=lambda result: next(index for index, case in enumerate(cases) if case["id"] == result["case_id"]))
    report = report_results(results, time.monotonic() - start, arguments.budget)
    (arguments.results / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"summary": report["summary"], "groups": report["groups"], "failures": report["failures"]}, indent=2))


if __name__ == "__main__":
    main()
