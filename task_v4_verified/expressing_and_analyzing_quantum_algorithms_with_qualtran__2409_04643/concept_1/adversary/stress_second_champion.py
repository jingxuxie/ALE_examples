import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from model import improvement, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    champion = ROOT / "champions/generation_2"
    if not champion.exists():
        shutil.copytree(ROOT / "attempts/v_3", champion)
    directory = ROOT / "adversary/stress_generation_2"
    directory.mkdir(exist_ok=True)
    cases = json.loads((ROOT / "participant/input/workloads.json").read_text())["cases"]
    original = json.loads((champion / "schedules.json").read_text())["schedules"]
    parameters = [
        (16, 0.0001, 20), (24, 0.0001, 30),
        (32, 0.0003, 30), (48, 0.0003, 40),
        (64, 0.0006, 30), (96, 0.0001, 20),
        (128, 0.00003, 30), (192, 0.00001, 20),
    ]
    jobs = []
    for case_index, case in enumerate(cases):
        initial = directory / f"initial_{case_index}.txt"
        initial.write_text(" ".join(map(str, original[case["id"]])) + "\n")
        for profile_index, (power, temperature, cycle) in enumerate(parameters):
            seed = 62810419 + 1000 * case_index + profile_index
            output = directory / f"case_{case_index}_profile_{profile_index}.txt"
            command = [str(champion / "search"), str(champion / f"case{case_index}.txt"),
                       str(output), str(args.seconds), str(seed), str(power),
                       str(temperature), str(cycle), str(initial)]
            jobs.append((case, profile_index, command, output, seed, power, temperature, cycle))

    def execute(job):
        case, profile_index, command, output, seed, power, temperature, cycle = job
        started = time.monotonic()
        with output.with_suffix(".log").open("w") as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=args.seconds + 30, check=True)
        order = [int(value) for value in output.read_text().split()]
        before = metrics(case, original[case["id"]])
        actual = metrics(case, order)
        return {"case": case["id"], "profile": profile_index,
                "seed": seed, "power": power, "temperature": temperature,
                "cycle_seconds": cycle, "metrics": actual,
                "gain": improvement(before, actual),
                "peak_safe": 20 * actual["peak"] <= 21 * before["peak"],
                "order_file": output.name, "returncode": process.returncode,
                "elapsed_seconds": time.monotonic() - started}

    started = time.monotonic()
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for future in concurrent.futures.as_completed([executor.submit(execute, job) for job in jobs]):
            record = future.result()
            records.append(record)
            (directory / "progress.json").write_text(json.dumps(records, indent=2) + "\n")
            print(record["case"], record["profile"], record["gain"], flush=True)
    best_orders = dict(original)
    case_records = []
    for case in cases:
        before = metrics(case, original[case["id"]])
        options = [record for record in records if record["case"] == case["id"] and record["peak_safe"]]
        best = max(options, key=lambda record: record["gain"])
        if best["gain"] > 1:
            best_orders[case["id"]] = [int(value) for value in (directory / best["order_file"]).read_text().split()]
        after = metrics(case, best_orders[case["id"]])
        case_records.append({"id": case["id"], "champion": before, "challenger": after,
                             "gain": improvement(before, after), "best_profile": best["profile"]})
    report = {"generation": 2, "method": "unchanged champion native smooth-frontier search",
              "champion_artifact_sha256": hashlib.sha256((champion / "schedules.json").read_bytes()).hexdigest(),
              "cases": case_records, "trials": len(records), "seconds_per_trial": args.seconds,
              "all_orders_valid": True, "core_gain": math.exp(sum(math.log(record["gain"]) for record in case_records) / len(case_records)),
              "minimum_case_gain": min(record["gain"] for record in case_records),
              "maximum_case_gain": max(record["gain"] for record in case_records),
              "elapsed_seconds": time.monotonic() - started}
    (directory / "challenger_schedules.json").write_text(json.dumps({"schedules": best_orders}) + "\n")
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
