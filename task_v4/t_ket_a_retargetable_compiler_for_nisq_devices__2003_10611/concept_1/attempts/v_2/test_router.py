import argparse
import collections
import glob
import io
import json
import math
import os
import random
import resource
import subprocess
import sys
import time
from unittest.mock import patch

from benchmark import validate
from solve import main as run_entry_point, safe_route, valid_route


def limit_memory():
    maximum = 2 * 1024 ** 3
    resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))


def execute(instance, budget=7.5):
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "solve.py"], input=json.dumps(instance), text=True,
        capture_output=True, timeout=12, preexec_fn=limit_memory,
        env={**os.environ, "ROUTER_BUDGET": str(budget), "ROUTER_DEBUG": "1"})
    assert result.returncode == 0, result.stderr
    score = validate(instance, json.loads(result.stdout))
    score["runtime"] = time.monotonic() - started
    score["diagnostic"] = result.stderr.strip()
    print(instance["id"], score, flush=True)
    return score


def check_entry_point_guards(instance):
    failures = [OSError("backend unavailable"), subprocess.TimeoutExpired("router", 9.8),
                subprocess.CompletedProcess([], 0, stdout="not JSON"),
                subprocess.CompletedProcess([], 0, stdout='{"operations":[]}')]
    for failure in failures:
        output = io.StringIO()
        behavior = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
        with patch("solve.subprocess.run", **behavior), patch("sys.stdin", io.StringIO(json.dumps(instance))), patch("sys.stdout", output):
            run_entry_point()
        result = json.loads(output.getvalue())
        assert valid_route(instance, result)
        validate(instance, result)


def relabel(instance, seed):
    generator = random.Random(seed)
    count = instance["n"]
    physical = list(range(count))
    logical = list(range(count))
    generator.shuffle(physical)
    generator.shuffle(logical)
    placement = [0] * count
    for original in range(count):
        placement[logical[original]] = physical[instance["initial"][original]]
    edges = [[physical[first], physical[second], weight] for first, second, weight in instance["edges"]]
    generator.shuffle(edges)
    for edge in edges:
        if generator.randrange(2):
            edge[0], edge[1] = edge[1], edge[0]
    return {**instance, "id": instance["id"] + "_relabel_" + str(seed),
            "initial": placement, "edges": edges,
            "gates": [[logical[first], logical[second]] for first, second in instance["gates"]]}


def random_instance(count, family, seed):
    generator = random.Random(seed)
    pairs = set()
    if family in ("chain", "ring", "modular"):
        pairs.update((physical, physical + 1) for physical in range(count - 1))
        if family == "ring":
            pairs.add((0, count - 1))
        elif family == "modular":
            for start in range(0, count, 4):
                for first in range(start, min(count, start + 4)):
                    for second in range(first + 1, min(count, start + 4)):
                        pairs.add((first, second))
    elif family == "tree":
        pairs.update(((physical - 1) // 2, physical) for physical in range(1, count))
    elif family == "star":
        pairs.update((0, physical) for physical in range(1, count))
    else:
        columns = 2 if family == "ladder" else 4
        for physical in range(count):
            if physical + columns < count:
                pairs.add((physical, physical + columns))
            if physical % columns < columns - 1 and physical + 1 < count:
                pairs.add((physical, physical + 1))
    placement = list(range(count))
    generator.shuffle(placement)
    return {"id": f"random_{family}_{count}_{seed}", "family": family,
            "n": count, "initial": placement,
            "edges": [[first, second, round(generator.uniform(0.45, 2.8), 4)] for first, second in sorted(pairs)],
            "gates": [generator.sample(range(count), 2) for _ in range(240)]}


def special_cases():
    edges = [[physical, physical + 1, 2.8 if physical == 0 else 0.45] for physical in range(11)]
    base = {"n": 12, "family": "chain", "initial": list(range(12)), "edges": edges}
    repeated = {**base, "id": "repeated_opaque_pair", "gates": [[0, 1], [1, 0]] * 48}
    check_entry_point_guards(repeated)
    result = execute(repeated, 1.0)
    assert result["cost"] < 70
    yield repeated["id"], result
    for name, gates in (
        ("nonembeddable_star", [[0, 1], [0, 2], [0, 3]] * 32),
        ("nonembeddable_triangle", [[0, 1], [1, 2], [2, 0]] * 32),
        ("independent_repeated_groups", [[0, 1]] * 24 + [[10, 11]] * 24 + [[1, 0]] * 24 + [[11, 10]] * 24),
        ("empty_program", []),
    ):
        instance = {**base, "id": name, "gates": gates}
        yield name, execute(instance, 1.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("assets")
    parser.add_argument("--relabel-seeds", type=int, default=2)
    parser.add_argument("--output", default="stress_results.json")
    arguments = parser.parse_args()
    results = dict(special_cases())
    ratios = collections.defaultdict(list)
    reference = json.load(open(os.path.join(arguments.assets, "baseline_scores.json")))
    for filename in sorted(glob.glob(os.path.join(arguments.assets, "public*.json"))):
        original = json.load(open(filename))
        for seed in range(arguments.relabel_seeds):
            instance = relabel(original, 600 + seed)
            result = execute(instance)
            result["ratio"] = result["cost"] / reference[original["id"]]["cost"]
            ratios[original["family"]].append(result["ratio"])
            results[instance["id"]] = result
    for count in (12, 20, 28):
        for family in ("chain", "ring", "grid", "ladder", "tree", "modular", "star"):
            instance = random_instance(count, family, 317 + count)
            safe = safe_route(instance)
            assert valid_route(instance, safe)
            assert len(safe["operations"]) <= len(instance["gates"]) * (count - 1)
            validate(instance, safe)
            results[instance["id"]] = execute(instance, 4.5)
    for family, values in ratios.items():
        quality = 1 - math.exp(sum(map(math.log, values)) / len(values))
        print("relabel quality", family, quality, flush=True)
        assert quality >= 0.30
    with open(arguments.output, "w") as stream:
        json.dump(results, stream, indent=2)
    print("PASSED", len(results), "cases; all within 12 seconds and 2 GiB")


if __name__ == "__main__":
    main()
