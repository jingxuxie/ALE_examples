import contextlib
import importlib.util
import json
import math
import os
import pathlib
import resource
import signal
import sys
import time


def handle_timeout(signum, frame):
    raise TimeoutError("case worker wall-time limit exceeded")


def main():
    submission = pathlib.Path(sys.argv[1])
    case_path = pathlib.Path(sys.argv[2])
    memory_bytes = int(sys.argv[3])
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024**3, 2 * 1024**3))
    os.sched_setaffinity(0, {int(sys.argv[4])})
    timeout = float(sys.argv[5]) if len(sys.argv) > 5 else None
    if timeout is not None:
        resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(timeout) + 1, math.ceil(timeout) + 2))
        signal.signal(signal.SIGALRM, handle_timeout)
        signal.setitimer(signal.ITIMER_REAL, timeout)
    sys.path.insert(0, str(submission))
    spec = importlib.util.spec_from_file_location("submitted_solver", submission / "solver.py")
    module = importlib.util.module_from_spec(spec)
    start = time.monotonic()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            spec.loader.exec_module(module)
            result = module.solve(json.loads(case_path.read_text()))
        if timeout is not None and time.monotonic() - start > timeout:
            raise TimeoutError("case worker wall-time limit exceeded")
        payload = {"ok": True, "result": result}
    except Exception as error:
        payload = {"ok": False, "error": type(error).__name__ + ": " + str(error),
                   "timeout": isinstance(error, TimeoutError)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    payload.update({"seconds": time.monotonic() - start,
               "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               "cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
               "cpu_affinity": sorted(os.sched_getaffinity(0))})
    print(json.dumps(payload, allow_nan=False, default=lambda value: value.tolist()))


if __name__ == "__main__":
    main()
