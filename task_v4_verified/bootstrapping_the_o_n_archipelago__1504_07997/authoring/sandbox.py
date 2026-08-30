import argparse
import ctypes
import errno
import json
import math
import os
from pathlib import Path
import resource
import sys


class RulesetAttribute(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathAttribute(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def filesystem_restrict(read_paths, write_paths):
    if os.uname().machine not in ("x86_64", "aarch64"):
        raise RuntimeError("unsupported architecture; no unsafe fallback")
    library = ctypes.CDLL(None, use_errno=True)
    library.syscall.restype = ctypes.c_long
    abi = library.syscall(444, 0, 0, 1)
    if abi < 1:
        raise RuntimeError("Landlock unavailable; no unsafe fallback")
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
              "kill", "tkill", "tgkill", "pidfd_send_signal", "sched_setaffinity",
              "fork", "vfork", "clone3", "truncate", "ftruncate", "chmod", "fchmod", "fchmodat",
              "chown", "fchown", "lchown", "fchownat", "utime", "utimes", "utimensat", "futimesat")
    try:
        for name in denied:
            number = library.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and library.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0) != 0:
                raise RuntimeError("seccomp rule failed: " + name)
        if library.seccomp_load(context) != 0:
            raise RuntimeError("seccomp load failed")
    finally:
        library.seccomp_release(context)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--participant", required=True)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--memory-mib", type=int, default=2048)
    parser.add_argument("--entry", default="solve.py")
    parser.add_argument("--extra-read", action="append", default=[])
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    submission = Path(arguments.submission).resolve(strict=True)
    participant = Path(arguments.participant).resolve(strict=True)
    scratch = Path(arguments.scratch).resolve(strict=True)
    entry = (submission / arguments.entry).resolve(strict=True)
    if submission not in entry.parents:
        raise ValueError("entry must be inside submission")
    for path in submission.rglob("*"):
        if path.is_symlink() or (path.is_file() and path.stat().st_nlink != 1):
            raise ValueError("submission links are forbidden")
        if not path.is_file() and not path.is_dir():
            raise ValueError("special submission file")
    read_paths = [submission, participant, Path(sys.executable).resolve()]
    for path in ("/usr", "/bin", "/lib", "/lib64", "/etc/ld.so.cache", "/etc/alternatives", "/dev/urandom"):
        if Path(path).exists():
            read_paths.append(Path(path))
    read_paths.extend(Path(path).resolve(strict=True) for path in arguments.extra_read)
    memory = arguments.memory_mib * 1024**2
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(arguments.seconds), math.ceil(arguments.seconds)+1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    available_cpus = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {available_cpus[os.getpid() % len(available_cpus)]})
    os.chdir(scratch)
    os.environ.clear()
    os.environ.update({"PATH": "/usr/bin:/bin", "HOME": str(scratch), "TMPDIR": str(scratch),
                       "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
                       "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                       "NUMBA_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1", "PYTHONHASHSEED": "0",
                       "PYTHONPATH": str(participant / "workspace") + os.pathsep + str(submission)})
    syscall_restrict()
    filesystem_restrict(read_paths, [scratch, "/dev/null"])
    parameters = arguments.arguments
    if parameters and parameters[0] == "--":
        parameters = parameters[1:]
    os.execv(sys.executable, [sys.executable, "-u", str(entry)] + parameters)


if __name__ == "__main__":
    main()
