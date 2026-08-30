"""Concept-local single-process tightening of the immutable shared sandbox."""

import ctypes
import errno
import importlib.util
import os
from pathlib import Path


for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
shared_path = Path(__file__).resolve().parents[2] / "authoring" / "sandbox_runner.py"
specification = importlib.util.spec_from_file_location("shared_runner", shared_path)
shared_runner = importlib.util.module_from_spec(specification)
specification.loader.exec_module(shared_runner)
original_confine = shared_runner.confine


def single_process_confine(read_paths, writable_path):
    import numpy
    import scipy.linalg
    import scipy.optimize
    abi = original_confine(read_paths, writable_path)
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
        raise RuntimeError("seccomp_init failed")
    try:
        for name in ("clone", "clone3"):
            number = library.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and library.seccomp_rule_add(context, 0x50000 | errno.EPERM, number, 0) != 0:
                raise RuntimeError("cannot deny " + name)
        if library.seccomp_load(context) != 0:
            raise RuntimeError("cannot enforce single process")
    finally:
        library.seccomp_release(context)
    return abi


shared_runner.confine = single_process_confine
if __name__ == "__main__":
    shared_runner.main()
