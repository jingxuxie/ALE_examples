import ctypes
import errno
import os
import signal
import sys


class Comparison(ctypes.Structure):
    _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_int),
                ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]


def restrict_accounting_syscalls():
    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                              ctypes.c_int, ctypes.c_uint,
                                              ctypes.POINTER(Comparison)]
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    context = library.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError("cannot initialize accounting syscall filter")

    def deny(name, comparisons=(), error=errno.EPERM):
        number = library.seccomp_syscall_resolve_name(name.encode("ascii"))
        if number == -1:
            return
        arguments = (Comparison * len(comparisons))(*comparisons)
        result = library.seccomp_rule_add_array(context, 0x00050000 | error,
                                                number, len(comparisons), arguments)
        if result != 0:
            raise RuntimeError("cannot restrict accounting syscall: " + name)

    try:
        for name in ("rt_sigaction", "sigaction"):
            deny(name, (Comparison(0, 4, signal.SIGCHLD, 0), Comparison(1, 1, 0, 0)))
        deny("signal", (Comparison(0, 4, signal.SIGCHLD, 0),))
        deny("clone3", error=errno.ENOSYS)
        for exit_signal in range(65):
            if exit_signal != signal.SIGCHLD:
                deny("clone", (Comparison(0, 7, 0x100FF, exit_signal),))
        for namespace_flag in (0x00020000, 0x02000000, 0x04000000, 0x08000000,
                               0x10000000, 0x20000000, 0x40000000):
            deny("clone", (Comparison(0, 7, namespace_flag, namespace_flag),))
        for name in ("unshare", "setns", "sched_setaffinity", "ptrace",
                     "process_vm_writev", "pidfd_getfd"):
            deny(name)
        if library.seccomp_load(context) != 0:
            raise RuntimeError("cannot load accounting syscall filter")
    finally:
        library.seccomp_release(context)


def main():
    library = ctypes.CDLL(None, use_errno=True)
    if library.prctl(4, 0, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "cannot protect resource reaper")
    if os.getpid() != 1 or len(sys.argv) < 2:
        raise RuntimeError("resource guard requires sandbox PID 1 and a command")
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    primary = os.fork()
    if primary == 0:
        try:
            restrict_accounting_syscalls()
            os.execv(sys.argv[1], sys.argv[1:])
        except BaseException as error:
            print("resource guard: " + str(error), file=sys.stderr, flush=True)
            os._exit(126)
    exit_code = 125
    while True:
        try:
            child, status, usage = os.wait4(-1, 0)
        except InterruptedError:
            continue
        except ChildProcessError:
            break
        if child == primary:
            exit_code = os.waitstatus_to_exitcode(status)
            if exit_code < 0:
                exit_code = 128 - exit_code
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
