import json
import math
import os
from pathlib import Path
import random
import subprocess
import time

from validate import ROOT, PARTICIPANT, query, write_job


def measure(path, label, timeout=120):
    start = time.perf_counter()
    try:
        subprocess.run([
            "python", str(ROOT / "solve.py"), "--input", str(path),
            "--output", str(ROOT / (label + ".result.json")),
        ], check=True, env=dict(os.environ, EEC_STATS="1"), timeout=timeout)
    except subprocess.TimeoutExpired:
        print(label, "TIMEOUT", flush=True)
        return
    print(label, "wall_seconds", time.perf_counter() - start, flush=True)


def main():
    generator = random.Random(612387)
    uniform = []
    for unused in range(139):
        radial = 0.38 * math.sqrt(generator.random())
        angle = 2 * math.pi * generator.random()
        uniform.append((100.0, radial * math.cos(angle), radial * math.sin(angle)))
    core = [(10 ** generator.uniform(-1, 1.8), generator.gauss(0, 0.09),
             generator.gauss(0, 0.09)) for unused in range(139)]
    for algorithm, resolution in [("ca", 8), ("ca", 64), ("ca", 1e10), ("kt", 0.03)]:
        queries = [query(order, kappa, algorithm, resolution)
                   for kappa in [1, 1.5, 2] for order in range(2, 9)]
        for label, event in [("uniform", uniform), ("core", core)]:
            name = f"stress_{label}_{algorithm}_{resolution}"
            path = write_job(name, [event], queries)
            measure(path, name)
    events = [[], [], []]
    for line in (PARTICIPANT / "input" / "sample.txt").read_text().splitlines():
        values = line.split()
        events[int(values[0])].append(tuple(map(float, values[1:])))
    queries = [query(order, kappa, algorithm, resolution)
               for algorithm, resolution in [("ca", 8), ("kt", 0.03)]
               for kappa in [1, 1.5, 2] for order in range(2, 9)]
    measure(write_job("throughput", events * 1000, queries), "throughput")


if __name__ == "__main__":
    main()
