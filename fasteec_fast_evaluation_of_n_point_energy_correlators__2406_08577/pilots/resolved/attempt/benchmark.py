import argparse
import array
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

import numpy as np

from solve import get_engine
from validate import read_events


ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent / "participant"


def measure(name, events, count, queries):
    with tempfile.TemporaryDirectory(prefix="benchmark-", dir=ROOT) as temporary:
        directory = Path(temporary)
        with (directory / "events.txt").open("w") as stream:
            for event_id in range(count):
                for particle in events[event_id % len(events)]:
                    stream.write(f"{event_id} " + " ".join(map(repr, particle)) + "\n")
        config = [f"{count} {len(queries)}"]
        for query in queries:
            config.append(" ".join(map(str, [query["order"], query["log_min"], query["bins"],
                query["ratio_bins"], query["phi_bins"], query.get("nu1", 1), query.get("nu2", 1),
                query.get("nu3", 1)])))
        start = time.perf_counter()
        cpu_start = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
        binary = os.environ.get("RESOLVED_BENCH_ENGINE") or str(get_engine())
        subprocess.run([binary, str(directory / "events.txt"), str(directory / "result.bin")],
                       input="\n".join(config) + "\n", text=True, check=True)
        elapsed = time.perf_counter() - start
        cpu = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime - cpu_start
        peak_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        print(f"{name}: {count} jets, {elapsed:.4f} s wall, {cpu:.4f} s CPU, "
              f"{count / elapsed:.1f} jets/s, child peak RSS {peak_rss} KiB", flush=True)
        with (directory / "result.bin").open("rb") as stream:
            for query in queries:
                size = query["bins"] * (query["ratio_bins"] * query["phi_bins"]) ** (query["order"] - 2)
                values = array.array("d")
                values.fromfile(stream, size)
                mass = math.fsum(values)
                if all(query.get(exponent, 1) == 1 for exponent in ("nu1", "nu2", "nu3")):
                    if query["order"] == 3:
                        expected = 1.0
                    else:
                        expected = 0.0
                        for event_id in range(count):
                            event = events[event_id % len(events)]
                            total = math.fsum(particle[0] for particle in event)
                            symmetric = [1., 0., 0., 0., 0.]
                            for particle in event:
                                weight = particle[0] / total
                                for degree in range(4, 0, -1):
                                    symmetric[degree] += symmetric[degree - 1] * weight
                            expected += 24 * symmetric[4] / count
                    assert abs(mass - expected) < 2e-10, (mass, expected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--mode", choices=("unit", "all", "high", "projected", "both"), default="both")
    arguments = parser.parse_args()
    queries = json.loads((PARTICIPANT / "input/sample.json").read_text())["queries"]
    events = read_events(PARTICIPANT / "input/sample.txt")[1:]
    if arguments.mode in ("unit", "both"):
        measure("sample unit 3+4", events, arguments.count, [queries[0], queries[3]])
    if arguments.mode in ("all", "both"):
        measure("sample all four", events, arguments.count, queries)
    if arguments.mode == "projected":
        measure("one-cell exact projection, all four", events, arguments.count,
                [dict(query, ratio_bins=1, phi_bins=1) for query in queries])
    rng = np.random.default_rng(419)
    event = np.column_stack((np.exp(rng.uniform(-3, 3, 139)), rng.normal(0, 0.16, 139),
                             rng.normal(3.13, 0.16, 139)))
    high = [[tuple(map(float, particle)) for particle in event]]
    if arguments.mode in ("high", "both"):
        measure("139 constituents, all four", high, max(2, arguments.count // 100), queries)


if __name__ == "__main__":
    main()
