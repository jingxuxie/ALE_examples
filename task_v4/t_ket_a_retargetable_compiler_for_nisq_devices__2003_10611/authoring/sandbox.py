import argparse
import ctypes
import errno
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time


class RulesetAttribute(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathAttribute(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def filesystem_restrict(read_paths, write_paths):
    library = ctypes.CDLL(None, use_errno=True)
    library.syscall.restype = ctypes.c_long
    abi = library.syscall(444, 0, 0, 1)
    if abi < 1:
        raise RuntimeError("Landlock unavailable; refusing unsafe execution")
    handled = (1 << (15 if abi >= 3 else 14 if abi >= 2 else 13)) - 1
    attribute = RulesetAttribute(handled)
    ruleset = library.syscall(444, ctypes.byref(attribute), ctypes.sizeof(attribute), 0)
    if ruleset < 0:
        raise OSError(ctypes.get_errno(), "Landlock ruleset creation")
    read_access = (1 << 0) | (1 << 2) | (1 << 3)
    try:
        for path, writable in [(path, False) for path in read_paths] + [(path, True) for path in write_paths]:
            path = Path(path).resolve(strict=True)
            descriptor = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                access = handled if writable else read_access
                if not path.is_dir():
                    access &= (1 << 0) | (1 << 1) | (1 << 2) | (1 << 14)
                rule = PathAttribute(access, descriptor)
                if library.syscall(445, ruleset, 1, ctypes.byref(rule), 0) < 0:
                    raise OSError(ctypes.get_errno(), "Landlock path rule")
            finally:
                os.close(descriptor)
        if library.prctl(38, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "no_new_privs")
        if library.syscall(446, ruleset, 0) != 0:
            raise OSError(ctypes.get_errno(), "Landlock restrict_self")
    finally:
        os.close(ruleset)


def syscall_restrict():
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
        raise RuntimeError("seccomp initialization failed")
    denied = ("socket", "socketpair", "connect", "bind", "listen", "accept", "accept4",
              "ptrace", "process_vm_readv", "process_vm_writev", "pidfd_getfd", "pidfd_open",
              "mount", "umount2", "pivot_root", "unshare", "setns", "bpf", "perf_event_open",
              "open_by_handle_at", "name_to_handle_at", "io_uring_setup", "userfaultfd",
              "kill", "tkill", "tgkill", "pidfd_send_signal", "sched_setaffinity")
    try:
        for name in denied:
            number = library.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and library.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0) != 0:
                raise RuntimeError("seccomp rule failed: " + name)
        if library.seccomp_load(context) != 0:
            raise RuntimeError("seccomp load failed")
    finally:
        library.seccomp_release(context)


def child(arguments):
    submission = Path(arguments.submission).resolve(strict=True)
    scratch = Path(arguments.scratch).resolve(strict=True)
    entry = (submission / arguments.entry).resolve(strict=True)
    if submission not in entry.parents:
        raise ValueError("entry must be inside submission")
    read_paths = [submission, Path(sys.executable).resolve()]
    for name in ("/usr", "/bin", "/lib", "/lib64", "/etc/ld.so.cache", "/etc/alternatives", "/dev/urandom"):
        if Path(name).exists():
            read_paths.append(Path(name))
    memory = arguments.memory_mb * 1024**2
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(arguments.seconds), math.ceil(arguments.seconds) + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024**2, 16 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {available[os.getpid() % len(available)]})
    os.chdir(submission)
    os.environ.clear()
    os.environ.update({"PATH": "/usr/bin:/bin", "HOME": str(scratch), "TMPDIR": str(scratch),
                       "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
                       "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                       "NUMBA_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1", "PYTHONHASHSEED": "0"})
    syscall_restrict()
    filesystem_restrict(read_paths, [submission, scratch, "/dev/null"])
    os.execv(sys.executable, [sys.executable, "-s", "-u", str(entry)])


def run_python(solution_dir, entry, payload, timeout, memory_mb=2048):
    solution = Path(solution_dir).resolve(strict=True)
    total_bytes = 0
    for path in solution.rglob("*"):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ValueError("submission links and special files forbidden")
        if path.is_file():
            total_bytes += path.stat().st_size
    if total_bytes > 128 * 1024**2:
        raise ValueError("submission exceeds 128 MiB")
    with tempfile.TemporaryDirectory(prefix="tket_eval_") as temporary:
        root = Path(temporary)
        copied = root / "submission"
        shutil.copytree(solution, copied)
        scratch = root / "scratch"
        scratch.mkdir()
        command = [sys.executable, "-I", str(Path(__file__).resolve()), "--child", "--submission", str(copied),
                   "--scratch", str(scratch), "--entry", entry, "--seconds", str(timeout),
                   "--memory-mb", str(memory_mb)]
        encoded = json.dumps(payload).encode()
        started = time.monotonic()
        with (root / "stdout").open("wb") as stdout, (root / "stderr").open("wb") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True)
            timed_out = False
            try:
                process.communicate(encoded, timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        return {"stdout": (root / "stdout").read_text(errors="replace"),
                "stderr": (root / "stderr").read_text(errors="replace"), "returncode": process.returncode,
                "seconds": time.monotonic() - started, "timed_out": timed_out}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--entry", default="solve.py")
    parser.add_argument("--seconds", type=float, default=8)
    parser.add_argument("--memory-mb", type=int, default=2048)
    child(parser.parse_args())
