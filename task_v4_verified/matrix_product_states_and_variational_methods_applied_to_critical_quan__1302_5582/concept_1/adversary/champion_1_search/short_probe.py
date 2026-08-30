import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "champion"))
from contractor import load_mps, measure


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (6, 7))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 ** 2, 8 * 1024 ** 2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_case(case_id):
    directory = ROOT / "runs" / case_id
    if directory.resolve().parent != (ROOT / "runs").resolve():
        raise ValueError("Case must be within this sidecar")
    request = json.loads((directory / "request.json").read_text())
    request.update(budget_seconds=6.0, wall_seconds=30.0)
    request_path = directory / "short_request.json"
    request_path.write_text(json.dumps(request, indent=2, allow_nan=False) + "\n")
    output_path = directory / "short.npz"
    command = ["/usr/bin/python", "-B", str(ROOT / "champion/solve.py"),
               "--request", str(request_path), "--output", str(output_path)]
    started = time.monotonic()
    timed_out = False
    with (directory / "short_stdout.log").open("wb") as stdout, (directory / "short_stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   preexec_fn=child_limits, start_new_session=True)
        while True:
            waited, status, usage = os.wait4(process.pid, os.WNOHANG)
            if waited:
                break
            if time.monotonic() - started > 30.0:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                _, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(0.01)
    process.returncode = os.waitstatus_to_exitcode(status)
    wall = time.monotonic() - started
    cpu = usage.ru_utime + usage.ru_stime
    record = {"case_id": case_id, "mode": "generation-only reviewed-copy standalone child; not evaluator certification",
              "cpu_accounting": "os.wait4 on the direct reviewed solver child, including Python/import/save CPU",
              "command": command, "returncode": process.returncode, "cpu_seconds": cpu,
              "wall_seconds": wall, "peak_rss_kib": usage.ru_maxrss, "timed_out": timed_out,
              "resources_valid": process.returncode == 0 and not timed_out and cpu <= 6 and wall <= 30,
              "stderr": (directory / "short_stderr.log").read_text(errors="replace"),
              "score": None}
    record["physical_validity"] = False
    if output_path.exists():
        try:
            record["measurement"] = measure(load_mps(output_path, request), request)
            record["physical_validity"] = True
        except (ValueError, OSError) as error:
            record["validation_error"] = str(error)
    record["valid_completed_short"] = record["physical_validity"] and record["resources_valid"]
    record["hashes"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in (request_path, output_path) if path.exists()}
    record["champion_source_hashes"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                        for path in sorted((ROOT / "champion").glob("*.py"))}
    (directory / "short_result.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(json.dumps(record, allow_nan=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", required=True)
    args = parser.parse_args()
    for case_id in args.case:
        run_case(case_id)


if __name__ == "__main__":
    main()
