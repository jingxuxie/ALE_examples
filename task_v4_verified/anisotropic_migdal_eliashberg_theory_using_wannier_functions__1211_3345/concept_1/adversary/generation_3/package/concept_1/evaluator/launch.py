"""Child-only adapter retaining the shared harness and enforcing no clone calls."""

import argparse
import ctypes
import errno
import runpy
import sys


def deny_process_and_thread_creation():
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
    try:
        for name in (b"clone", b"clone3"):
            number = library.seccomp_syscall_resolve_name(name)
            if number >= 0 and library.seccomp_rule_add(context, 0x50000 | errno.EPERM, number, 0) != 0:
                raise RuntimeError("cannot prohibit process/thread creation")
        if library.seccomp_load(context) != 0:
            raise RuntimeError("cannot load process/thread restriction")
    finally:
        library.seccomp_release(context)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--shared-runner", required=True)
    arguments, remaining = parser.parse_known_args()
    shared = runpy.run_path(arguments.shared_runner, run_name="shared_hardened_runner")
    original = shared["confine"]

    def complete_confinement(read_paths, writable_path):
        abi = original(read_paths, writable_path)
        deny_process_and_thread_creation()
        return abi

    shared["main"].__globals__["confine"] = complete_confinement
    sys.argv = [arguments.shared_runner] + remaining
    shared["main"]()


if __name__ == "__main__":
    main()
