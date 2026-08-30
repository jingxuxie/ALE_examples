import ctypes
import errno
import json
import os
from pathlib import Path
import resource
import runpy
import signal
import subprocess
import sys
import time
import traceback


def restrict_processes():
    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    context = library.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError("Cannot initialize seccomp")
    blocked = ("clone", "clone3", "fork", "vfork", "execve", "execveat", "ptrace",
               "process_vm_readv", "process_vm_writev", "socket", "socketpair", "connect",
               "unshare", "setns", "mount", "umount2", "bpf", "perf_event_open",
               "io_uring_setup", "open_by_handle_at", "pidfd_getfd", "keyctl", "reboot")
    try:
        for name in blocked:
            syscall = library.seccomp_syscall_resolve_name(name.encode())
            if syscall >= 0 and library.seccomp_rule_add(context, 0x00050000 | errno.EPERM, syscall, 0) != 0:
                raise RuntimeError("Cannot add seccomp rule")
        if library.seccomp_load(context) != 0:
            raise RuntimeError("Cannot load seccomp")
    finally:
        library.seccomp_release(context)


def main():
    if "--solver-child" in sys.argv:
        request = json.loads(Path("/work/request.json").read_text())
        cpu_limit = int(request["budget_seconds"])
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 1))
        restrict_processes()
        sys.path.insert(0, "/submission")
        sys.argv = ["/submission/solve.py", "--request", "/work/request.json", "--output", "/work/state.npz"]
        runpy.run_path(sys.argv[0], run_name="__main__")
        return
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError("Cannot protect supervisor memory")
    report_path = Path("/work/resource.json")
    descriptor = os.open(report_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    identity = os.fstat(descriptor)
    request = json.loads(Path("/work/request.json").read_text())
    wall_limit = float(request["wall_seconds"])
    started = time.monotonic()
    process = subprocess.Popen(["/usr/bin/python", "-I", "-B", "/worker.py", "--solver-child"], close_fds=True)
    timed_out = False

    def expire(signum, frame):
        nonlocal timed_out
        timed_out = True
        try:
            os.kill(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    previous_handler = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, max(1e-6, wall_limit - (time.monotonic() - started)))
    try:
        _, status, usage = os.wait4(process.pid, 0)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    elapsed = time.monotonic() - started
    process.returncode = os.waitstatus_to_exitcode(status)
    current = report_path.lstat()
    if (current.st_dev, current.st_ino, current.st_nlink) != (identity.st_dev, identity.st_ino, 1):
        raise RuntimeError("Resource report path was tampered with")
    code = os.waitstatus_to_exitcode(status)
    report = {"cpu_seconds": usage.ru_utime + usage.ru_stime,
              "worker_wall_seconds": elapsed, "worker_timed_out": timed_out,
              "worker_exitcode": code, "accounting": "protected supervisor wait4 on direct solver child"}
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.ftruncate(descriptor, 0)
    os.write(descriptor, (json.dumps(report, allow_nan=False) + "\n").encode())
    os.close(descriptor)
    os._exit(code if code >= 0 else 128 - code)


if __name__ == "__main__":
    main()
