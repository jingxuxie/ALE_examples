import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def unique_pairs(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate JSON object key")
        output[key] = value
    return output


def reject_constant(value):
    raise ValueError("nonfinite JSON number " + value)


def simulate(case, order):
    count = len(case["nodes"])
    if type(order) is not list or len(order) != count:
        raise ValueError("wrong schedule size")
    done = set()
    live = {}
    entering = [[] for _ in range(count)]
    leaving = [[] for _ in range(count)]
    for edge_index, (source, destination, width) in enumerate(case["edges"]):
        leaving[source].append((edge_index, width))
        entering[destination].append((edge_index, width))
    peak = 0
    area = 0
    for node_index in order:
        if type(node_index) is not int or not 0 <= node_index < count or node_index in done:
            raise ValueError("schedule is not an integer permutation")
        input_width = 0
        for edge_index, width in entering[node_index]:
            if edge_index not in live:
                raise ValueError("edge consumed before production")
            input_width += live.pop(edge_index)
        output_width = sum(width for _, width in leaving[node_index])
        operation = case["nodes"][node_index]
        during = sum(live.values()) + max(input_width, output_width) + operation["workspace"]
        area += during * operation["duration"]
        live.update(leaving[node_index])
        peak = max(peak, during, sum(live.values()))
        done.add(node_index)
    if live or len(done) != count or peak <= 0 or area <= 0:
        raise ValueError("incomplete computation")
    return {"peak": peak, "qubit_time": area}


def evaluate(submission):
    started = time.monotonic()
    try:
        artifact = submission / "schedules.json"
        if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 16 * 1024**2:
            raise ValueError("missing, linked or oversized schedules.json")
        candidate = json.loads(artifact.read_text(), object_pairs_hook=unique_pairs,
                               parse_constant=reject_constant)
        if type(candidate) is not dict or set(candidate) != {"schedules"}:
            raise ValueError("invalid top-level schema")
        schedules = candidate["schedules"]
        bank = json.loads((HERE / "hidden" / "workloads.json").read_text())
        baselines = json.loads((HERE / "hidden" / "baseline_metrics.json").read_text())
        if type(schedules) is not dict or set(schedules) != {case["id"] for case in bank["cases"]}:
            raise ValueError("missing or extra workload IDs")
        records = []
        families = defaultdict(list)
        peak_guard = True
        for case in bank["cases"]:
            metrics = simulate(case, schedules[case["id"]])
            before = baselines[case["id"]]
            log_ratio = 0.7 * math.log(before["peak"] / metrics["peak"]) + 0.3 * math.log(before["qubit_time"] / metrics["qubit_time"])
            families[case["family"]].append(log_ratio)
            peak_guard &= 20 * metrics["peak"] <= 21 * before["peak"]
            records.append({"id": case["id"], "family": case["family"],
                            "ratio": math.exp(log_ratio), "baseline": before, **metrics})
        family_scores = {family: math.exp(sum(values) / len(values)) for family, values in families.items()}
        core = math.exp(sum(math.log(record["ratio"]) for record in records) / len(records))
        worst = min(family_scores.values())
        worst_case = min(record["ratio"] for record in records)
        passed = core >= 1.06 and worst_case >= 1.02 and peak_guard
        return {"core_score": core, "worst_family_score": worst, "family_scores": family_scores,
                "worst_case_score": worst_case,
                "runtime_seconds": time.monotonic() - started, "resource_score": core,
                "passed": passed, "valid": True, "peak_guard": peak_guard,
                "reason": "target reached" if passed else "fixed resource-improvement target not reached",
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "cases": records}
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as error:
        return {"core_score": 0.0, "worst_family_score": 0.0, "resource_score": 0.0,
                "runtime_seconds": time.monotonic() - started, "passed": False, "valid": False,
                "reason": str(error)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = evaluate(args.submission)
    text = json.dumps(report, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
