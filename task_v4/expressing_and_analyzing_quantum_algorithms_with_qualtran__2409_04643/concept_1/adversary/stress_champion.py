import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LEGACY_PARTICIPANT = ROOT / "adversary/generations/generation_1/participant"
if not LEGACY_PARTICIPANT.exists():
    LEGACY_PARTICIPANT = ROOT / "participant"
sys.path.insert(0, str(LEGACY_PARTICIPANT / "workspace"))
from model import metrics, improvement

spec = importlib.util.spec_from_file_location("generator", ROOT / "adversary/build.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def orders(directory, cases):
    return {case["id"]: [int(value) for value in (directory / (case["id"] + ".txt")).read_text().split()] for case in cases}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion-seconds", type=int, default=60)
    parser.add_argument("--challenger-seconds", type=int, default=180)
    args = parser.parse_args()
    directory = ROOT / "adversary/stress_generation_1"
    directory.mkdir(exist_ok=True)
    champion = ROOT / "champions/generation_1"
    cases = []
    for family_index, family in enumerate(("modular", "wavefront", "reconvergent", "heterogeneous")):
        for offset in range(6):
            case = generator.make_case(52409600 + 100 * family_index + offset, family, scale=1 + (offset % 2))
            cases.append(case)
    input_path = directory / "workloads.json"
    input_path.write_text(json.dumps({"cases": cases}))
    environment = os.environ.copy()
    environment.update({"PARTICIPANT": str(LEGACY_PARTICIPANT), "INPUT": str(input_path),
                        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "4"})
    with (directory / "seed_search.log").open("w") as log:
        subprocess.run([sys.executable, str(champion / "explore.py")], cwd=directory,
                       env=environment, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    baseline_dir = directory / "champion"
    baseline_dir.mkdir(exist_ok=True)
    started = time.monotonic()
    with (directory / "champion.log").open("w") as log:
        subprocess.run([str(champion / "optimize"), str(args.champion_seconds), "12873", str(baseline_dir)],
                       cwd=directory, env=environment, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=60 + math.ceil(len(cases)/4) * (args.champion_seconds + 10))
    baseline_orders = orders(baseline_dir, cases)
    for case in cases:
        metrics(case, baseline_orders[case["id"]])
    best_orders = dict(baseline_orders)
    best_metrics = {case["id"]: metrics(case, baseline_orders[case["id"]]) for case in cases}
    runs = []
    for seed in (912773, 519327):
        challenger_dir = directory / f"challenger_{seed}"
        challenger_dir.mkdir(exist_ok=True)
        for case in cases:
            (challenger_dir / (case["id"] + ".txt")).write_text(" ".join(map(str, best_orders[case["id"]])))
        with (directory / f"challenger_{seed}.log").open("w") as log:
            subprocess.run([str(champion / "optimize"), str(args.challenger_seconds), str(seed), str(challenger_dir)],
                           cwd=directory, env=environment, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=60 + math.ceil(len(cases)/4) * (args.challenger_seconds + 10))
        current_orders = orders(challenger_dir, cases)
        for case in cases:
            actual = metrics(case, current_orders[case["id"]])
            before = metrics(case, baseline_orders[case["id"]])
            if 20 * actual["peak"] <= 21 * before["peak"] and improvement(best_metrics[case["id"]], actual) > 1:
                best_metrics[case["id"]] = actual
                best_orders[case["id"]] = current_orders[case["id"]]
        runs.append({"seed": seed, "seconds_per_case": args.challenger_seconds})
        (directory / "progress.json").write_text(json.dumps({"completed_challengers": runs, "elapsed_seconds": time.monotonic() - started}, indent=2))
    records = []
    for case in cases:
        before = metrics(case, baseline_orders[case["id"]])
        after = best_metrics[case["id"]]
        records.append({"id": case["id"], "family": case["family"], "nodes": len(case["nodes"]),
                        "champion": before, "challenger": after, "gain": improvement(before, after)})
    report = {"cases": records, "cases_tested": len(cases), "champion_valid_on_all": True,
              "maximum_gain": max(record["gain"] for record in records),
              "elapsed_seconds": time.monotonic() - started, "champion_seconds_per_case": args.champion_seconds,
              "challenger_runs": runs, "root_cause": "finite-budget topological frontier search; no semantic failures"}
    (directory / "report.json").write_text(json.dumps(report, indent=2))
    (directory / "champion_schedules.json").write_text(json.dumps({"schedules": baseline_orders}))
    (directory / "challenger_schedules.json").write_text(json.dumps({"schedules": best_orders}))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
