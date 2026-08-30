import json
import os
import resource
import subprocess
import time
from pathlib import Path


def limits():
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 31))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024**2, 16 * 1024**2))


def main():
    started = time.monotonic()
    result = {}
    with open("/work/planner.stdout", "w") as stdout, open("/work/planner.stderr", "w") as stderr:
        try:
            process = subprocess.run(["/usr/bin/python3", "/submission/solve.py", "/work/input.json", "/work/output.json"],
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     timeout=30, preexec_fn=limits)
            result["returncode"] = process.returncode
            result["timed_out"] = False
        except subprocess.TimeoutExpired:
            result["returncode"] = -1
            result["timed_out"] = True
    result["planner_seconds"] = time.monotonic() - started
    result["stderr"] = Path("/work/planner.stderr").read_text(errors="replace")[-2000:]
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
