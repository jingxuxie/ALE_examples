import ctypes
import json
import os
import resource
import subprocess
import sys


def main():
    audit_fd = int(sys.argv[1])
    os.set_inheritable(audit_fd, False)
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(4, 0, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "PR_SET_DUMPABLE")
    process = subprocess.Popen(sys.argv[2:], close_fds=True)
    root_status = None
    waited_cpu = 0.
    waited_count = 0
    waited = []
    while True:
        try:
            child_pid, status, usage = os.wait4(-1, 0)
        except InterruptedError:
            continue
        except ChildProcessError:
            break
        if child_pid == process.pid:
            root_status = status
        waited_cpu += usage.ru_utime + usage.ru_stime
        waited_count += 1
        if len(waited) < 16:
            waited.append(dict(pid=child_pid, status=status, cpu_seconds=usage.ru_utime + usage.ru_stime))
    if root_status is None:
        raise RuntimeError("root_policy_not_reaped")
    own = resource.getrusage(resource.RUSAGE_SELF)
    report = dict(guardian_pid=os.getpid(), root_pid=process.pid,
                  guardian_dumpable=library.prctl(3, 0, 0, 0, 0),
                  guardian_cpu=own.ru_utime + own.ru_stime, waited_cpu=waited_cpu,
                  cpu_seconds=waited_cpu + own.ru_utime + own.ru_stime,
                  waited_count=waited_count, first_waited_records=waited,
                  root_status=root_status)
    encoded = (json.dumps(report, separators=(",", ":")) + "\n").encode()
    if len(encoded) > 4096:
        raise RuntimeError("audit_record_too_large")
    os.write(audit_fd, encoded)
    os.close(audit_fd)
    process.returncode = os.waitstatus_to_exitcode(root_status)
    return process.returncode if process.returncode >= 0 else 128 - process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
