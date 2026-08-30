import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time


def make_instance(family, mode, seed):
    generator = random.Random(seed)
    count = generator.choice([12, 16, 20, 24, 28])
    raw_edges = set()

    def connect(first, second):
        raw_edges.add(tuple(sorted((first, second))))

    if family in ("chain", "ring"):
        for physical in range(count - 1):
            connect(physical, physical + 1)
        if family == "ring":
            connect(0, count - 1)
    elif family in ("grid", "ladder"):
        height = 2 if family == "ladder" else 4
        width = count // height
        for row in range(height):
            for column in range(width):
                physical = row * width + column
                if row + 1 < height:
                    connect(physical, physical + width)
                if column + 1 < width:
                    connect(physical, physical + 1)
    elif family == "tree":
        for physical in range(1, count):
            parent = (physical - 1) // 2 if mode % 2 else generator.randrange(physical)
            connect(parent, physical)
    else:
        size = count // 4
        for cluster in range(4):
            for local in range(size):
                connect(cluster * size + local, cluster * size + (local + 1) % size)
            if cluster:
                connect((cluster - 1) * size + generator.randrange(size), cluster * size + generator.randrange(size))
    labels = list(range(count))
    generator.shuffle(labels)
    edges = [[labels[first], labels[second], round(generator.uniform(0.45, 2.8), 4)]
             for first, second in sorted(raw_edges)]
    initial = list(range(count))
    generator.shuffle(initial)
    gate_count = [96, 144, 180, 216, 240, 192][mode]
    gates = []
    while len(gates) < gate_count:
        logicals = list(range(count))
        generator.shuffle(logicals)
        if mode == 0:
            gates.extend([logicals[offset:offset + 2] for offset in range(0, count, 2)])
        elif mode == 1:
            hub_first, hub_second = logicals[:2]
            for other in logicals[2:]:
                gates.append([generator.choice([hub_first, hub_second]), other])
            gates.append([hub_first, hub_second])
        elif mode == 2:
            for repeat in range(3):
                gates.extend([[logicals[offset], logicals[(offset + 1) % count]] for offset in range(count)])
        elif mode == 3:
            gates.extend([generator.sample(range(count), 2) for repeat in range(count)])
        elif mode == 4:
            for repeat in range(4):
                for offset in range(count):
                    neighbor = (offset + generator.choice([1, 1, 1, 2])) % count
                    gates.append([logicals[offset], logicals[neighbor]])
        else:
            pairs = [[first, second] for first in logicals for second in logicals if first < second]
            generator.shuffle(pairs)
            gates.extend(pairs)
    return dict(id=f"stress_{family}_{mode}", family=family, n=count, edges=edges,
                initial=initial, gates=gates[:gate_count])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--time", type=float, default=1)
    parser.add_argument("--tag", default="stress")
    parser.add_argument("--modes", type=int, default=6)
    args = parser.parse_args()
    participant = Path(__file__).resolve().parents[2] / "participant"
    sys.dont_write_bytecode = True

    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result

    validator = module("validator", participant / "workspace/routing.py")
    baseline = module("baseline", participant / "baseline/solve.py")
    directory = Path(args.tag)
    directory.mkdir(exist_ok=True)
    cases = Path("stress_cases")
    cases.mkdir(exist_ok=True)
    all_ratios = []
    summaries = {}
    for family_id, family in enumerate(["chain", "ring", "grid", "ladder", "tree", "modular"]):
        ratios = []
        for mode in range(args.modes):
            instance = make_instance(family, mode, 1739 + family_id * 100 + mode)
            (cases / (instance["id"] + ".json")).write_text(json.dumps(instance))
            baseline_file = cases / (instance["id"] + ".baseline.json")
            if baseline_file.exists():
                baseline_score = json.loads(baseline_file.read_text())
            else:
                baseline_score = validator.validate(instance, baseline.solve(instance))
                baseline_file.write_text(json.dumps(baseline_score))
            start = time.monotonic()
            process = subprocess.run([sys.executable, "solve.py"], input=json.dumps(instance),
                                     text=True, capture_output=True, timeout=args.time + 6,
                                     env=dict(os.environ, ROUTE_TIME=str(args.time), ROUTE_DEBUG="1"))
            elapsed = time.monotonic() - start
            if process.returncode:
                raise RuntimeError(process.stderr)
            answer = json.loads(process.stdout)
            score = validator.validate(instance, answer)
            ratio = score["cost"] / baseline_score["cost"]
            ratios.append(ratio)
            print(f'{instance["id"]:21} n={instance["n"]:2} {score["cost"]:9.2f} base={baseline_score["cost"]:9.2f} gain={100*(1-ratio):6.2f}% {elapsed:.3f}s', flush=True)
            (directory / (instance["id"] + ".route.json")).write_text(process.stdout)
            (directory / (instance["id"] + ".log")).write_text(process.stderr)
            summaries[instance["id"]] = dict(score, ratio=ratio, seconds=elapsed)
        all_ratios.extend(ratios)
        print(f"{family}: {100*(1-math.exp(sum(map(math.log,ratios))/len(ratios))):.3f}%", flush=True)
    print(f"overall: {100*(1-math.exp(sum(map(math.log,all_ratios))/len(all_ratios))):.3f}%", flush=True)
    (directory / "summary.json").write_text(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
