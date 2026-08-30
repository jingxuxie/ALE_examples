import argparse
import json
from pathlib import Path
import resource
import sys
import time

sys.dont_write_bytecode = True
from privileged_planner import Planner, ROOT, check, score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--local-width", type=int, default=8)
    parser.add_argument("--scale", type=float, default=3.0)
    parser.add_argument("--waypoints", type=int, default=2)
    parser.add_argument("--heuristic-weight", type=float, default=1.0)
    parser.add_argument("--anchors", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads((ROOT / "evaluator" / "hidden" / "cases.json").read_text())
    config = {key: value for key, value in vars(args).items() if key != "output"}
    rows = []
    answers = []
    started = time.perf_counter()
    cpu_started = time.process_time()
    for case in cases:
        case_started = time.perf_counter()
        answer = Planner(case["instance"]).beam(**config)
        result = check(case["instance"], answer)
        row = {"id": case["id"], "family": case["family"], "baseline_cost": case["baseline"]["cost"], "ratio": result["cost"] / case["baseline"]["cost"], "elapsed_seconds": time.perf_counter() - case_started, **result}
        rows.append(row)
        answers.append(answer)
        report = {**score(rows), "config": config, "cases": rows, "complete": len(rows) == len(cases), "elapsed_seconds": time.perf_counter() - started, "cpu_seconds": time.process_time() - cpu_started, "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".plans.jsonl").write_text("".join(json.dumps(answer, separators=(",", ":")) + "\n" for answer in answers))
        print(json.dumps(row, separators=(",", ":")), flush=True)
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
