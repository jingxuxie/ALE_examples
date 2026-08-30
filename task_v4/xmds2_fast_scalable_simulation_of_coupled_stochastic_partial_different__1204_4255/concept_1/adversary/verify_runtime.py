import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from privileged_planner import ROOT, check, score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--anchor", action="store_true")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    cases = json.loads((ROOT / "evaluator" / "hidden" / "cases.json").read_text())
    payload = "".join(json.dumps(case["instance"], separators=(",", ":")) + "\n" for case in cases)
    affinity = min(os.sched_getaffinity(0))
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}

    def limits():
        os.sched_setaffinity(0, {affinity})
        resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
        resource.setrlimit(resource.RLIMIT_CPU, (120, 121))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 ** 2, 64 * 1024 ** 2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    planner_name = "anchor_planner.py" if args.anchor else ("compact_planner.py" if args.compact else "privileged_planner.py")
    command = ["/usr/bin/python3", "-u", "-s", str(here / planner_name)]
    if not args.compact and not args.anchor:
        command += ["--level", str(args.level)]
    suffix = "anchor" if args.anchor else ("compact" if args.compact else "level" + str(args.level))
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    timed_out = False
    with (here / ("runtime_" + suffix + ".plans.jsonl")).open("w+") as output:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.PIPE, env=environment, preexec_fn=limits, text=True)
        try:
            unused, error = process.communicate(payload, timeout=120)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            unused, error = process.communicate()
        elapsed = time.perf_counter() - started
        output.seek(0)
        lines = output.read().splitlines()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    rows = []
    if process.returncode == 0 and not timed_out and len(lines) == len(cases):
        for case, line in zip(cases, lines):
            result = check(case["instance"], json.loads(line))
            rows.append({"id": case["id"], "family": case["family"], "baseline_cost": case["baseline"]["cost"], "ratio": result["cost"] / case["baseline"]["cost"], **result})
    result = {"valid": len(rows) == len(cases), "cases": rows, "timed_out": timed_out, "returncode": process.returncode, "stderr": error, "elapsed_seconds": elapsed, "cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, "maxrss_kib": after.ru_maxrss, "cpu_affinity": [affinity], "address_space_limit": 1024 ** 3, "cpu_limit_seconds": 120, "network_isolated": False, "scope": "Direct single-process pinned-CPU resource verification, not the bubblewrap evaluator", "command": command, "planner_sha256": hashlib.sha256(Path(command[3]).read_bytes()).hexdigest()}
    if rows:
        result.update(score(rows))
    (here / ("runtime_" + suffix + ".json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
