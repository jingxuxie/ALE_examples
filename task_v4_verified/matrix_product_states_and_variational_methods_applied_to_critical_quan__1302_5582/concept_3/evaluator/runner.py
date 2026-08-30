import ctypes
import errno
import json
import os
from pathlib import Path
import resource
import runpy
import sys


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
    limits = json.loads(Path("/limits.json").read_text())
    resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"], limits["cpu_seconds"] + 1))
    memory = limits["address_space_mib"] * 1024 ** 2
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits["output_bytes"], limits["output_bytes"]))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.umask(0o077)
    restrict_processes()
    sys.path.insert(0, "/submission")
    sys.argv = ["/submission/predict.py", "--input", "/input.json", "--train",
                "/public/train.json", "--output", "/output/predictions.json"]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
