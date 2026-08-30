#!/usr/bin/python3 -I
import ctypes
import errno
import fcntl
import os
from pathlib import Path
import sys


DENIED_SYSCALLS = (
    "socket", "socketpair", "socketcall", "connect", "bind", "listen", "accept", "accept4",
    "sendto", "sendmsg", "sendmmsg", "recvfrom", "recvmsg", "recvmmsg", "shutdown",
    "io_uring_setup", "io_uring_enter", "io_uring_register", "ptrace",
    "process_vm_readv", "process_vm_writev", "pidfd_open", "pidfd_getfd", "kcmp",
    "mount", "umount2", "pivot_root", "chroot", "unshare", "setns",
    "open_by_handle_at", "name_to_handle_at", "bpf",
)


def network_filter():
    if os.uname().machine != "x86_64":
        raise ValueError("This audited adapter supports only x86_64")
    library = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    context = library.seccomp_init(0x7FFF0000)
    if not context:
        raise RuntimeError("Cannot initialize seccomp")
    descriptor = os.memfd_create("isolation-network-deny", os.MFD_ALLOW_SEALING)
    try:
        for name in DENIED_SYSCALLS:
            number = library.seccomp_syscall_resolve_name(name.encode())
            if number == -1:
                raise ValueError(f"Unknown syscall: {name}")
            result = library.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0)
            if result < 0:
                raise OSError(-result, f"Cannot deny {name}")
        result = library.seccomp_export_bpf(context, descriptor)
        if result < 0:
            raise OSError(-result, "Cannot export seccomp filter")
        os.lseek(descriptor, 0, os.SEEK_SET)
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE)
        os.set_inheritable(descriptor, True)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise
    finally:
        library.seccomp_release(context)


def main():
    arguments = sys.argv[1:]
    executable = Path(__file__).resolve().with_name("bwrap.real")
    if not executable.is_file():
        executable = Path("/usr/bin/bwrap")
    if arguments in (["--help"], ["--version"]):
        os.execv(executable, [str(executable)] + arguments)
    if "--" not in arguments:
        raise ValueError("Refusing bubblewrap arguments without an explicit command separator")
    separator = arguments.index("--")
    options = arguments[:separator]
    payload = arguments[separator:]
    if "--unshare-all" in options or "--share-net" in options:
        raise ValueError("Unexpected implicit or explicitly shared network policy")
    descriptor = network_filter()
    options = ["--add-seccomp-fd" if value == "--seccomp" else value for value in options if value != "--unshare-net"]
    options.extend(["--add-seccomp-fd", str(descriptor)])
    print("ISOLATION_ADAPTER: filesystem arguments retained; network namespace replaced by inherited deny-network seccomp; existing filters retained", file=sys.stderr, flush=True)
    os.execv(executable, [str(executable)] + options + payload)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ISOLATION_ADAPTER_REFUSED: {error}", file=sys.stderr)
        raise SystemExit(2)
