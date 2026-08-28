import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time

from validate import PARTICIPANT, ROOT, query, write_job


def main():
    events = [[], [], []]
    for line in (PARTICIPANT / "input" / "sample.txt").read_text().splitlines():
        fields = line.split()
        events[int(fields[0])].append(tuple(map(float, fields[1:])))
    queries = [query(order, kappa, algorithm, resolution)
               for algorithm, resolution in [("ca", 8), ("kt", 0.03)]
               for kappa in [1, 1.5, 2] for order in range(2, 9)]
    path = write_job("large_batch", events * 33333 + [events[0]], queries)
    output = ROOT / "large_batch.result.json"
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    start = time.perf_counter()
    subprocess.run(["python", str(ROOT / "solve.py"), "--input", str(path), "--output", str(output)],
                   env=dict(os.environ, EEC_STATS="1"), check=True, timeout=120)
    elapsed = time.perf_counter() - start
    histograms = json.loads(output.read_text())["histograms"]
    largest_error = 0
    for specification, histogram in zip(queries, histograms):
        expected = 0
        for event, count in zip(events, [33334, 33333, 33333]):
            total = sum(particle[0] for particle in event)
            expected += count / 100000 * sum((particle[0] / total) ** specification["kappa"]
                                            for particle in event) ** specification["order"]
        assert all(math.isfinite(value) and value >= 0 for value in histogram)
        largest_error = max(largest_error, abs(sum(histogram) - expected) / expected)
    summary = dict(nevents=100000, queries=len(queries), wall_seconds=elapsed,
                   maximum_relative_mass_error=largest_error,
                   child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    print(json.dumps(summary), flush=True)
    (ROOT / "large_batch.summary.json").write_text(json.dumps(summary, indent=2))
    assert largest_error < 1e-8
    (ROOT / "large_batch.txt").unlink()
    path.unlink()


if __name__ == "__main__":
    main()
