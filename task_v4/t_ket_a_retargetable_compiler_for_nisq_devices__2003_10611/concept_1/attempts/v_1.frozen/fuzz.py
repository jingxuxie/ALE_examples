import argparse
import importlib.util
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--native")
    parser.add_argument("--time", type=float, default=0.04)
    args = parser.parse_args()
    participant = Path(__file__).resolve().parents[2] / "participant"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("validator", participant / "workspace/routing.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    maximum_time = 0
    generator = random.Random(1972198)
    for case_id in range(args.count):
        count = generator.randint(12, 28)
        gate_count = generator.randint(96, 240)
        edges = set()
        for physical in range(1, count):
            parent = physical - 1 if case_id % 5 == 0 else 0 if case_id % 5 == 1 else generator.randrange(physical)
            edges.add((parent, physical))
        if case_id % 5 in (3, 4):
            probability = 0.15 if case_id % 5 == 3 else 0.7
            for first in range(count):
                for second in range(first + 1, count):
                    if generator.random() < probability:
                        edges.add((first, second))
        weighted = []
        for first, second in sorted(edges):
            weight = generator.choice([0.45, 2.8]) if case_id % 3 == 0 else round(generator.uniform(0.45, 2.8), 4)
            weighted.append([first, second, weight])
        initial = list(range(count))
        generator.shuffle(initial)
        gates = []
        for gate_id in range(gate_count):
            if case_id % 7 == 0:
                pair = [0, 1]
            elif case_id % 7 == 1:
                pair = [0, generator.randrange(1, count)]
            else:
                pair = generator.sample(range(count), 2)
            if generator.random() < 0.5:
                pair.reverse()
            gates.append(pair)
        instance = dict(id=f"fuzz_{case_id}", family="tree", n=count, gates=gates, edges=weighted, initial=initial)
        command = [sys.executable, "solve.py"]
        payload = json.dumps(instance)
        if args.native:
            command = [args.native]
            fields = [count, gate_count, len(weighted)] + initial
            fields.extend(value for edge in weighted for value in edge)
            fields.extend(value for gate in gates for value in gate)
            payload = " ".join(map(str, fields))
        start = time.monotonic()
        process = subprocess.run(command, input=payload, text=True, capture_output=True, timeout=7.5,
                                 env=dict(os.environ, ROUTE_TIME=str(args.time)))
        elapsed = time.monotonic() - start
        maximum_time = max(maximum_time, elapsed)
        if process.returncode:
            Path("fuzz_failure.json").write_text(json.dumps(instance))
            raise RuntimeError(process.stderr)
        try:
            score = validator.validate(instance, json.loads(process.stdout))
            assert score["valid"]
        except Exception:
            Path("fuzz_failure.json").write_text(json.dumps(instance))
            Path("fuzz_failure.route.json").write_text(process.stdout)
            raise
        if case_id % 20 == 19:
            print(f"Validated {case_id + 1} cases; maximum runtime {maximum_time:.3f}s", flush=True)
    print(json.dumps(dict(cases=args.count, valid=True, maximum_seconds=maximum_time,
                         maximum_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)))


if __name__ == "__main__":
    main()
