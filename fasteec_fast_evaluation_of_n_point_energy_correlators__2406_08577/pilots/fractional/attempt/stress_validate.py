import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import solve


DIRECTORY = Path(__file__).resolve().parent


def resource_limits():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    affinity = os.sched_getaffinity(0)
    os.sched_setaffinity(0, {min(affinity)})


def main():
    base_path = DIRECTORY / "benchmark.json"
    base_job = json.loads(base_path.read_text())
    base_events = base_job["nevents"]
    nevents = 100000
    if nevents % base_events:
        raise ValueError("Run validate.py with a benchmark count dividing 100000 first")
    base_lines = (DIRECTORY / base_job["events_file"]).read_text().splitlines()
    rows = [line.split(maxsplit=1) for line in base_lines]
    del base_lines
    events_path = DIRECTORY / "stress_events.txt"
    with events_path.open("w") as output:
        for block in range(nevents // base_events):
            offset = block * base_events
            output.writelines(f"{int(event_id) + offset} {coordinates}\n"
                              for event_id, coordinates in rows)
    constituent_count = len(rows) * (nevents // base_events)
    del rows
    job = {**base_job, "nevents": nevents, "events_file": events_path.name}
    job_path = DIRECTORY / "stress_job.json"
    result_path = DIRECTORY / "stress_result.json"
    job_path.write_text(json.dumps(job))
    solve.executable()
    start = time.perf_counter()
    subprocess.run(
        [sys.executable, str(DIRECTORY / "solve.py"), "--input", str(job_path),
         "--output", str(result_path)],
        check=True, cwd=DIRECTORY.parent / "participant", preexec_fn=resource_limits,
    )
    elapsed = time.perf_counter() - start
    peak_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    result = json.loads(result_path.read_text())["histograms"]
    expected = solve.compute(base_job, base_path)["histograms"]
    difference = max(abs(actual - reference)
                     for histogram, baseline in zip(result, expected)
                     for actual, reference in zip(histogram, baseline))
    assert difference < 2e-11
    report = dict(nevents=nevents, constituents=constituent_count,
                  cpu_affinity_count=1, address_space_limit_gib=3,
                  elapsed_seconds=elapsed, peak_resident_mib=peak_rss / 1024,
                  repetition_max_error=difference,
                  normalization_max_error=max(abs(sum(histogram) - 1) for histogram in result))
    (DIRECTORY / "stress_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    events_path.unlink()
    job_path.unlink()


if __name__ == "__main__":
    main()
