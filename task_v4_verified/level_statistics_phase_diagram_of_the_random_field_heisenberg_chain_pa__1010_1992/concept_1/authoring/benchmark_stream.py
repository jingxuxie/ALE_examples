import argparse
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def read_line(process, seconds):
    deadline = time.monotonic() + seconds
    output = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while b"\n" not in output:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("Streaming response timed out")
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Submission closed stdout early")
            output.extend(chunk)
            if len(output) > 16000000:
                raise ValueError("Excessive output")
    return bytes(output).split(b"\n", 1)[0]


def benchmark(cases):
    cpus = sorted(os.sched_getaffinity(0))[:4]
    command = ["taskset", "--cpu-list", ",".join(map(str, cpus)), "prlimit",
               "--as=2147483648", "--", sys.executable,
               str(ROOT / "participant/workspace/predict.py")]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                     "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[variable] = "4"
    public_cases = {"cases": [{key: case[key] for key in ("id", "L", "fields")} for case in cases]}
    request = (json.dumps(public_cases, allow_nan=False) + "\n").encode()
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=environment, start_new_session=True)
    try:
        if read_line(process, 60) != b"READY":
            raise ValueError("Expected READY before delivery of cases")
        startup_seconds = time.monotonic() - started
        process.stdin.write(request)
        process.stdin.flush()
        started = time.monotonic()
        predictions = json.loads(read_line(process, 12))
        inference_seconds = time.monotonic() - started
        process.stdin.close()
        process.wait(timeout=5)
        if process.returncode:
            raise RuntimeError(process.stderr.read().decode())
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    lookup = {record["id"]: record["f"] for record in predictions["predictions"]}
    overall = (sum((lookup[case["id"]] - case["f"]) ** 2 for case in cases) / len(cases)) ** 0.5
    return {"startup_seconds": startup_seconds, "inference_seconds": inference_seconds,
            "startup_limit_seconds": 60, "inference_limit_seconds": 3,
            "meets_streaming_time_limits": startup_seconds <= 60 and inference_seconds <= 3,
            "overall_rmse": overall, "cpu_affinity": cpus, "address_space_mb": 2048,
            "records": len(cases), "official_isolated_evaluation": False,
            "note": "Local subprocess with CPU affinity and address-space limit; no filesystem sandbox"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    cases = [json.loads(line) for line in (ROOT / "participant/input/validation.jsonl").read_text().splitlines()]
    results = [benchmark(cases) for repeat in range(args.repeats)]
    report = {"runs": results, "all_within_limits": all(result["meets_streaming_time_limits"] for result in results)}
    (ROOT / "participant/input/streaming_benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
