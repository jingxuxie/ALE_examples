import argparse
import ctypes
import json
import os
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path


def process_usage():
    ticks = os.sysconf("SC_CLK_TCK")
    page_size = os.sysconf("SC_PAGE_SIZE")
    cpu_ticks = 0
    resident_bytes = 0
    children = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        identifier = int(entry.name)
        try:
            fields = (entry / "stat").read_text().rsplit(") ", 1)[1].split()
        except (OSError, IndexError):
            continue
        if identifier == 1:
            cpu_ticks += int(fields[13]) + int(fields[14])
        else:
            cpu_ticks += sum(int(fields[position]) for position in (11, 12, 13, 14))
            resident_bytes += max(0, int(fields[21])) * page_size
            children.append(identifier)
    return cpu_ticks / ticks, resident_bytes, children


def reap(main_identifier):
    main_status = None
    while True:
        try:
            identifier, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return main_status
        if identifier == 0:
            return main_status
        if identifier == main_identifier:
            main_status = os.waitstatus_to_exitcode(status)


def terminate_all():
    for iteration in range(200):
        _, _, identifiers = process_usage()
        if not identifiers:
            return
        for identifier in identifiers:
            try:
                os.kill(identifier, signal.SIGKILL)
            except ProcessLookupError:
                pass
        reap(-1)
        time.sleep(0.01)
    raise RuntimeError("namespace descendants did not terminate")


def main():
    if os.getpid() != 1:
        raise RuntimeError("resource guard must be PID 1 in a private PID namespace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", type=float, default=120.0)
    parser.add_argument("--memory", type=int, default=2 * 1024 ** 3)
    parser.add_argument("--wall", type=float, default=180.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    ctypes.CDLL(None).prctl(4, 0, 0, 0, 0)
    started = time.monotonic()
    process = subprocess.Popen(arguments.command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    peak_resident_bytes = 0
    reason = "ok"
    returncode = None
    try:
        while returncode is None:
            cpu_seconds, resident_bytes, _ = process_usage()
            peak_resident_bytes = max(peak_resident_bytes, resident_bytes)
            if cpu_seconds > arguments.cpu:
                confirm_cpu, _, _ = process_usage()
                if confirm_cpu > arguments.cpu:
                    reason = "aggregate_cpu_limit"
                    break
            if resident_bytes > arguments.memory:
                reason = "aggregate_memory_limit"
                break
            if time.monotonic() - started > arguments.wall:
                reason = "guard_wall_limit"
                break
            returncode = reap(process.pid)
            if returncode is None:
                time.sleep(0.02)
        process.returncode = returncode
    finally:
        terminate_all()
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu_seconds = usage.ru_utime + usage.ru_stime
        if cpu_seconds > arguments.cpu:
            reason = "aggregate_cpu_limit"
        if returncode not in (None, 0) and reason == "ok":
            reason = "worker_nonzero_exit"
        report = {"cpu_seconds": cpu_seconds, "peak_rss_bytes": peak_resident_bytes,
                  "reason": reason, "worker_returncode": returncode,
                  "wall_seconds": time.monotonic() - started}
        sys.stderr.write("\nMBE_GUARD_RESOURCE " + json.dumps(report, allow_nan=False) + "\n")
        sys.stderr.flush()
    sys.exit(0 if reason == "ok" and returncode == 0 else 125)


if __name__ == "__main__":
    main()
