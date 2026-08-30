import json
import os
import resource
import sys
import time


DIAGNOSTIC_VERSION = "infra5-private-phase-v1"
PHASES = ("early_python", "before_rlimit", "after_rlimit", "before_seccomp_load", "before_runpy")
phase_descriptor = None


def emit_phase(phase):
    if phase_descriptor is None:
        return
    own = resource.getrusage(resource.RUSAGE_SELF)
    descendants = resource.getrusage(resource.RUSAGE_CHILDREN)
    payload = {"phase": phase, "pid": os.getpid(),
               "cpu_user_seconds": own.ru_utime, "cpu_system_seconds": own.ru_stime,
               "cpu_process_seconds": time.process_time(),
               "children_user_seconds": descendants.ru_utime,
               "children_system_seconds": descendants.ru_stime,
               "monotonic_seconds": time.monotonic(),
               "rlimit_cpu": list(resource.getrlimit(resource.RLIMIT_CPU))}
    encoded = (json.dumps(payload, allow_nan=False, separators=(",", ":")) + "\n").encode()
    if len(encoded) > 1024 or os.write(phase_descriptor, encoded) != len(encoded):
        raise RuntimeError("Incomplete diagnostic phase write")


if "--solver-child" in sys.argv:
    position = sys.argv.index("--diagnostic-fd")
    phase_descriptor = int(sys.argv[position + 1])
    emit_phase("early_python")

import ctypes
import errno
from pathlib import Path
import runpy
import signal
import subprocess
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
        emit_phase("before_seccomp_load")
        if library.seccomp_load(context) != 0:
            raise RuntimeError("Cannot load seccomp")
    finally:
        library.seccomp_release(context)


def main():
    if "--solver-child" in sys.argv:
        request = json.loads(Path("/work/request.json").read_text())
        cpu_limit = int(request["budget_seconds"])
        emit_phase("before_rlimit")
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit + 2, cpu_limit + 3))
        emit_phase("after_rlimit")
        restrict_processes()
        sys.path.insert(0, "/submission")
        sys.argv = ["/submission/solve.py", "--request", "/work/request.json", "--output", "/work/state.npz"]
        emit_phase("before_runpy")
        os.close(phase_descriptor)
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
    phase_reader, phase_writer = os.pipe2(os.O_CLOEXEC)
    parent_before = resource.getrusage(resource.RUSAGE_SELF)
    started = time.monotonic()
    process = subprocess.Popen(["/usr/bin/python", "-I", "-B", "/worker.py", "--solver-child",
                                "--diagnostic-fd", str(phase_writer)], close_fds=True,
                               pass_fds=(phase_writer,))
    os.close(phase_writer)
    phase_bytes = bytearray()
    phase_error = ""
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
        try:
            while True:
                chunk = os.read(phase_reader, min(1024, 4097 - len(phase_bytes)))
                if not chunk:
                    break
                phase_bytes.extend(chunk)
                if len(phase_bytes) > 4096:
                    raise RuntimeError("Diagnostic phase channel exceeded its bound")
        except Exception as error:
            phase_error = str(error)[:160]
            try:
                os.kill(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        _, status, usage = os.wait4(process.pid, 0)
    finally:
        os.close(phase_reader)
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    elapsed = time.monotonic() - started
    process.returncode = os.waitstatus_to_exitcode(status)
    current = report_path.lstat()
    if (current.st_dev, current.st_ino, current.st_nlink) != (identity.st_dev, identity.st_ino, 1):
        raise RuntimeError("Resource report path was tampered with")
    code = os.waitstatus_to_exitcode(status)
    phases = []
    try:
        for line in bytes(phase_bytes).splitlines():
            phase = json.loads(line)
            if phase["pid"] != process.pid:
                raise ValueError("Unexpected diagnostic child PID")
            phase["wall_since_spawn_seconds"] = phase["monotonic_seconds"] - started
            phases.append(phase)
    except (ValueError, TypeError, KeyError) as error:
        phase_error = (phase_error + "; " + str(error))[:160]
    parent_after = resource.getrusage(resource.RUSAGE_SELF)
    report = {"cpu_seconds": usage.ru_utime + usage.ru_stime,
              "worker_wall_seconds": elapsed, "worker_timed_out": timed_out,
              "worker_exitcode": code, "accounting": "protected supervisor wait4 on direct solver child",
              "diagnostic_version": DIAGNOSTIC_VERSION,
              "wait4_ru_utime": usage.ru_utime, "wait4_ru_stime": usage.ru_stime,
              "wait4_status": status, "solver_pid": process.pid, "supervisor_pid": os.getpid(),
              "phases": phases, "phase_error": phase_error,
              "phase_channel_bytes": len(phase_bytes),
              "phase_channel_complete": not phase_error and tuple(item["phase"] for item in phases) == PHASES,
              "parent_cpu_before": {"user": parent_before.ru_utime, "system": parent_before.ru_stime},
              "parent_cpu_after_reap": {"user": parent_after.ru_utime, "system": parent_after.ru_stime},
              "parent_cpu_interval": {"user": parent_after.ru_utime - parent_before.ru_utime,
                                      "system": parent_after.ru_stime - parent_before.ru_stime}}
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.ftruncate(descriptor, 0)
    os.write(descriptor, (json.dumps(report, allow_nan=False) + "\n").encode())
    os.close(descriptor)
    os._exit(code if code >= 0 else 128 - code)


if __name__ == "__main__":
    main()
