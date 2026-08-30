import ctypes
import json
import os
import resource
import subprocess
import sys


def main():
    system = ctypes.CDLL(None, use_errno=True)
    if system.prctl(4, 0, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "cannot protect accounting descriptors")
    if system.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "cannot enable descendant accounting")
    with open("/output/solver.log", "wb") as log:
        child = subprocess.Popen(["/usr/bin/python3", "/submission/solve.py", "--input", "/input/case.json", "--output", "/output/result.npz"], stdout=log, stderr=log, close_fds=True)
        user_seconds = 0.0
        system_seconds = 0.0
        maximum_rss = 0
        returncode = None
        reaped = 0
        while True:
            try:
                waited, status, usage = os.wait4(-1, 0)
            except ChildProcessError:
                break
            reaped += 1
            user_seconds += usage.ru_utime
            system_seconds += usage.ru_stime
            maximum_rss = max(maximum_rss, usage.ru_maxrss)
            if waited == child.pid:
                returncode = os.waitstatus_to_exitcode(status)
                child.returncode = returncode
    own = resource.getrusage(resource.RUSAGE_SELF)
    report = {
        "schema_version": 1,
        "returncode": returncode,
        "cpu_user_seconds": user_seconds,
        "cpu_system_seconds": system_seconds,
        "cpu_seconds": user_seconds + system_seconds,
        "monitor_cpu_seconds": own.ru_utime + own.ru_stime,
        "maximum_rss_kib": maximum_rss,
        "reaped_children": reaped,
        "accounting_kind": "protected trusted in-sandbox parent wait4 and subreaper; submission stdout and descriptors separated",
    }
    print(json.dumps(report, allow_nan=False), flush=True)
    return 0 if returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
