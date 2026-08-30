import argparse
import ctypes
import errno
import json
import os
from pathlib import Path
import resource
import runpy
import sys
import time


class RulesetAttribute(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathAttribute(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int)]


def confine(read_paths, writable_path):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    abi = libc.syscall(444, 0, 0, 1)
    if abi < 1:
        raise RuntimeError("Landlock unavailable; refusing unisolated evaluation")
    handled = (1 << 13) - 1
    if abi >= 2:
        handled |= 1 << 13
    if abi >= 3:
        handled |= 1 << 14
    if abi >= 5:
        handled |= 1 << 15
    attribute = RulesetAttribute(handled)
    ruleset = libc.syscall(444, ctypes.byref(attribute), ctypes.sizeof(attribute), 0)
    if ruleset < 0:
        raise OSError(ctypes.get_errno(), "landlock_create_ruleset")
    try:
        for raw_path, writable in [(path, False) for path in read_paths] + [(writable_path, True)]:
            path = Path(raw_path).resolve()
            if not path.exists():
                continue
            descriptor = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                access = handled if writable else (1 << 0) | (1 << 2) | (1 << 3)
                if not path.is_dir():
                    access &= (1 << 0) | (1 << 1) | (1 << 2) | (1 << 14)
                rule = PathAttribute(access, descriptor)
                if libc.syscall(445, ruleset, 1, ctypes.byref(rule), 0) < 0:
                    raise OSError(ctypes.get_errno(), "landlock_add_rule: " + str(path))
            finally:
                os.close(descriptor)
        if libc.prctl(38, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "PR_SET_NO_NEW_PRIVS")
        if libc.syscall(446, ruleset, 0) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self")
    finally:
        os.close(ruleset)
    seccomp = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    seccomp.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    context = seccomp.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError("seccomp_init failed")
    forbidden = (
        "socket", "socketpair", "connect", "bind", "listen", "accept", "accept4",
        "ptrace", "process_vm_readv", "process_vm_writev", "pidfd_getfd",
        "execve", "execveat", "fork", "vfork", "setsid", "setpgid",
        "kill", "tkill", "tgkill", "mount", "umount2", "setns", "unshare",
        "truncate", "truncate64", "ftruncate", "ftruncate64",
        "open_by_handle_at", "io_uring_setup", "io_uring_enter", "io_uring_register",
        "chmod", "fchmod", "fchmodat", "fchmodat2", "chown", "fchown", "lchown",
        "fchownat", "utime", "utimes", "futimesat", "utimensat", "bpf",
        "reboot", "kexec_load"
    )
    try:
        for name in forbidden:
            number = seccomp.seccomp_syscall_resolve_name(name.encode())
            if number >= 0:
                result = seccomp.seccomp_rule_add(context, 0x50000 | errno.EPERM, number, 0)
                if result != 0:
                    raise RuntimeError("seccomp rule failed: " + name)
        if seccomp.seccomp_load(context) != 0:
            raise RuntimeError("seccomp_load failed")
    finally:
        seccomp.seccomp_release(context)
    return abi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--participant", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--cpu-seconds", type=int, default=180)
    parser.add_argument("--memory-mb", type=int, default=4096)
    parser.add_argument("--entry", default="solve.py")
    arguments = parser.parse_args()
    submission = Path(arguments.submission).resolve()
    participant = Path(arguments.participant).resolve()
    scratch = Path(arguments.scratch).resolve()
    input_path = Path(arguments.input).resolve()
    output_path = Path(arguments.output).resolve()
    if scratch not in output_path.parents or scratch not in input_path.parents:
        raise ValueError("Only scratch-contained public input and output are permitted")
    if not (submission / arguments.entry).is_file():
        raise FileNotFoundError(submission / arguments.entry)
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "MKL_NUM_THREADS",
                "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "GOTO_NUM_THREADS"):
        os.environ[key] = "1"
    for key in list(os.environ):
        if any(marker in key.upper() for marker in ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "CODEX")):
            del os.environ[key]
    os.environ["HOME"] = str(scratch)
    os.environ["TMPDIR"] = str(scratch)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["ALE_PUBLIC_INPUT"] = str(participant / "input")
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("LD_PRELOAD", None)
    sys.dont_write_bytecode = True
    resource.setrlimit(resource.RLIMIT_AS, (arguments.memory_mb * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (arguments.cpu_seconds, arguments.cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.chdir(scratch)
    sys.path[:] = [str(submission), str(participant / "workspace")] + [
        path for path in sys.path if path.startswith("/usr/")
    ]
    allowed_runtime = ["/usr", "/lib", "/lib64", "/bin", "/etc/ld.so.cache",
                       "/etc/localtime", "/dev/null", "/dev/urandom", "/dev/random"]
    abi = confine(allowed_runtime + [submission, participant], scratch)
    entry = str(submission / arguments.entry)
    sys.argv = [entry, "--input", str(input_path), "--output", str(output_path)]
    started = time.process_time()
    try:
        runpy.run_path(entry, run_name="__main__")
    finally:
        print(json.dumps({"sandbox": "landlock-seccomp", "landlock_abi": abi,
                          "candidate_cpu_seconds": time.process_time() - started}), file=sys.stderr)


if __name__ == "__main__":
    main()
