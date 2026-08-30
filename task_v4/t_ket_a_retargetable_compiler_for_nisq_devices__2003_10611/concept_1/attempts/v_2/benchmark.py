import argparse
import collections
import glob
import json
import math
import os
import subprocess
import sys
import time


def validate(instance, result):
    positions = instance["initial"][:]
    occupants = [0] * instance["n"]
    for logical, physical in enumerate(positions):
        occupants[physical] = logical
    weights = {tuple(sorted((first, second))): weight for first, second, weight in instance["edges"]}
    previous = [-1] * instance["n"]
    predecessors = []
    for index, pair in enumerate(instance["gates"]):
        predecessors.append({previous[logical] for logical in pair} - {-1})
        for logical in pair:
            previous[logical] = index
    done = set()
    depths = [0] * instance["n"]
    work = 0.0
    swaps = 0
    assert len(result["operations"]) <= 30000
    for operation in result["operations"]:
        if operation[0] == "swap":
            assert len(operation) == 3
            first, second = operation[1:]
            assert 0 <= first < instance["n"] and 0 <= second < instance["n"]
            duration = 3
            occupants[first], occupants[second] = occupants[second], occupants[first]
            positions[occupants[first]] = first
            positions[occupants[second]] = second
            swaps += 1
        else:
            assert operation[0] == "gate" and len(operation) == 2
            index = operation[1]
            assert 0 <= index < len(instance["gates"])
            assert index not in done and predecessors[index] <= done
            done.add(index)
            first, second = [positions[logical] for logical in instance["gates"][index]]
            duration = 1
        assert tuple(sorted((first, second))) in weights, (operation, first, second)
        work += duration * weights[tuple(sorted((first, second)))]
        depths[first] = depths[second] = max(depths[first], depths[second]) + duration
    assert len(done) == len(instance["gates"])
    return {"cost": work + 0.05 * max(depths), "work": work, "depth": max(depths), "swaps": swaps}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("assets")
    parser.add_argument("--pattern", default="public*.json")
    parser.add_argument("--budget", type=float, default=1.5)
    parser.add_argument("--output", default="benchmark_results.json")
    arguments = parser.parse_args()
    reference = json.load(open(os.path.join(arguments.assets, "baseline_scores.json")))
    results = {}
    ratios = collections.defaultdict(list)
    for filename in sorted(glob.glob(os.path.join(arguments.assets, arguments.pattern))):
        instance = json.load(open(filename))
        started = time.monotonic()
        run = subprocess.run([sys.executable, "solve.py"], input=json.dumps(instance), text=True,
                             capture_output=True, timeout=12,
                             env={**os.environ, "ROUTER_BUDGET": str(arguments.budget), "ROUTER_DEBUG": "1"})
        if run.returncode:
            raise RuntimeError(run.stderr)
        result = validate(instance, json.loads(run.stdout))
        result["runtime"] = time.monotonic() - started
        result["ratio"] = result["cost"] / reference[instance["id"]]["cost"]
        results[instance["id"]] = result
        ratios[instance["family"]].append(result["ratio"])
        ratios["overall"].append(result["ratio"])
        print(instance["id"], result, run.stderr.strip(), flush=True)
    for family, values in ratios.items():
        print(family, "quality", 1 - math.exp(sum(map(math.log, values)) / len(values)))
    with open(arguments.output, "w") as stream:
        json.dump(results, stream, indent=2)


if __name__ == "__main__":
    main()
