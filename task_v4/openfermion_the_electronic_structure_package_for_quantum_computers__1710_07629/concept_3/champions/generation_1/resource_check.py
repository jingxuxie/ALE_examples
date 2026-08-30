import ctypes
import errno
from pathlib import Path
import resource
import runpy
import sys
import time


def main():
    start = time.perf_counter()
    resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (131072, 131072))
    library = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_rule_add.restype = ctypes.c_int
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_load.restype = ctypes.c_int
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    context = library.seccomp_init(0x7fff0000)
    if not context:
        raise RuntimeError('seccomp initialization failed')
    for name in (
        'clone', 'clone3', 'fork', 'vfork', 'execve', 'execveat',
        'socket', 'connect', 'accept', 'accept4', 'ptrace',
        'process_vm_readv', 'process_vm_writev', 'kill', 'tkill', 'tgkill',
        'unshare', 'setns',
    ):
        syscall = library.seccomp_syscall_resolve_name(name.encode())
        if syscall >= 0:
            result = library.seccomp_rule_add(context, 0x00050000 | errno.EPERM, syscall, 0)
            if result != 0:
                raise RuntimeError(f'seccomp rule failed: {name}: {result}')
    result = library.seccomp_load(context)
    library.seccomp_release(context)
    if result != 0:
        raise RuntimeError(f'seccomp load failed: {result}')
    sys.argv = sys.argv[1:]
    sys.dont_write_bytecode = True
    runpy.run_path(str(Path(sys.argv[0]).resolve()), run_name='__main__')
    usage = resource.getrusage(resource.RUSAGE_SELF)
    print('resource check:', {
        'wall_seconds': time.perf_counter() - start,
        'cpu_seconds': usage.ru_utime + usage.ru_stime,
        'peak_rss_kib': usage.ru_maxrss,
        'process_thread_network_creation': 'denied',
    })


if __name__ == '__main__':
    main()
